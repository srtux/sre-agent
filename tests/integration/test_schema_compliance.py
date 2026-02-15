"""Integration test: verify all Pydantic models enforce extra='forbid'.

This test automatically discovers all BaseModel subclasses in sre_agent/
and verifies they declare model_config with extra='forbid'. Serves as
a regression gate to prevent new models from accidentally accepting
unknown fields.
"""

import importlib
import inspect
import pkgutil
from typing import Any

import pytest
from pydantic import BaseModel

# Models with intentional exceptions — document why
KNOWN_EXCEPTIONS: dict[str, str] = {
    "InvestigationState": "Has mutating methods (add_finding, transition_phase, etc.); uses extra='forbid' but not frozen=True",
}


def _discover_models() -> list[tuple[str, type[BaseModel]]]:
    """Discover all BaseModel subclasses in the sre_agent package."""
    import sre_agent

    models: list[tuple[str, type[BaseModel]]] = []
    package_path = sre_agent.__path__
    prefix = sre_agent.__name__ + "."

    for _importer, modname, _ispkg in pkgutil.walk_packages(
        package_path, prefix=prefix
    ):
        # Skip test files, deployment scripts, etc.
        if any(
            skip in modname for skip in ("test_", "_test", "deploy", "eval", "scripts")
        ):
            continue
        try:
            module = importlib.import_module(modname)
        except Exception:
            continue

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseModel)
                and obj is not BaseModel
                and obj.__module__ == modname  # Only classes defined in this module
            ):
                models.append((f"{modname}.{name}", obj))

    return models


# Discover at module load time (once)
_ALL_MODELS = _discover_models()


class TestSchemaCompliance:
    """Verify all Pydantic BaseModel subclasses enforce extra='forbid'."""

    @pytest.mark.parametrize(
        "fqn,model_cls",
        _ALL_MODELS,
        ids=[fqn for fqn, _ in _ALL_MODELS],
    )
    def test_model_has_extra_forbid(self, fqn: str, model_cls: type[BaseModel]) -> None:
        """Every model must have extra='forbid' in model_config."""
        class_name = model_cls.__name__
        if class_name in KNOWN_EXCEPTIONS:
            pytest.skip(f"Known exception: {KNOWN_EXCEPTIONS[class_name]}")

        config: dict[str, Any] = getattr(model_cls, "model_config", {})
        extra = config.get("extra")
        assert extra == "forbid", (
            f"{fqn} missing model_config extra='forbid' "
            f"(found: {extra!r}). Add: "
            f"model_config = ConfigDict(frozen=True, extra='forbid')"
        )

    def test_discovered_models_not_empty(self) -> None:
        """Sanity check: we should discover at least 10 models."""
        assert len(_ALL_MODELS) >= 10, (
            f"Only found {len(_ALL_MODELS)} models — discovery may be broken"
        )
