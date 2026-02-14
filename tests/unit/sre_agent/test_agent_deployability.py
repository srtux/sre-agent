import copy
from unittest.mock import patch

import pytest
from vertexai.preview.reasoning_engines import AdkApp

from sre_agent.agent import root_agent


def find_lock_in_obj(obj, path="root", seen=None):
    if seen is None:
        seen = set()

    obj_id = id(obj)
    if obj_id in seen:
        return []
    seen.add(obj_id)

    results = []
    # Check if this object IS a lock
    if "_thread.lock" in str(type(obj)):
        results.append(f"🚩 FOUND LOCK at {path}: {type(obj)}")

    try:
        if hasattr(obj, "__dict__"):
            for k, v in obj.__dict__.items():
                results.extend(find_lock_in_obj(v, f"{path}.{k}", seen))
        if isinstance(obj, list):
            for i, v in enumerate(obj):
                results.extend(find_lock_in_obj(v, f"{path}[{i}]", seen))
        if isinstance(obj, dict):
            for k, v in obj.items():
                results.extend(find_lock_in_obj(v, f"{path}[{k!r}]", seen))
    except Exception:
        pass
    return results


def test_agent_is_deepcopyable():
    """Verify that the root_agent can be deepcopied.

    This is critical for Vertex AI Reasoning Engine deployment, as the
    agent_engines.create() call deepcopies the agent before packaging.
    Failure to deepcopy (often due to non-pickleable locks in model clients)
    will break deployment.
    """
    try:
        # This will fail if any attribute contains a non-pickleable lock
        copied_agent = copy.deepcopy(root_agent)
        assert copied_agent is not None
        assert copied_agent.name == root_agent.name
    except Exception as e:
        locks = find_lock_in_obj(root_agent)
        lock_info = "\n".join(locks)
        pytest.fail(
            f"Agent failed deepcopy (broken deployment): {e}\nFound locks:\n{lock_info}"
        )


def test_adk_app_is_deepcopyable():
    """Verify that AdkApp containing the agent is deepcopyable."""
    try:
        # Patch the _project attribute directly on the global_config singleton
        # We patch at the module level where it's instantiated if possible, but here
        # we can modify the instance directly as it's a singleton.
        import google.cloud.aiplatform.initializer

        # Temporarily set the project ID to avoid auth checks during AdkApp init
        original_project = google.cloud.aiplatform.initializer.global_config._project
        google.cloud.aiplatform.initializer.global_config._project = "mock-project"

        try:
            app = AdkApp(agent=root_agent)
            copied_app = copy.deepcopy(app)
            assert copied_app is not None
        finally:
            # Restore original state
            google.cloud.aiplatform.initializer.global_config._project = original_project

    except Exception as e:
        locks = find_lock_in_obj(root_agent)
        lock_info = "\n".join(locks)
        pytest.fail(
            f"AdkApp failed deepcopy (broken deployment): {e}\nFound locks:\n{lock_info}"
        )
