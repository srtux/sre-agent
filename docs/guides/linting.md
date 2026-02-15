# Linting Strategy

We enforce a "Zero Broken Windows" policy. Linting is not a suggestion; it is a hard requirement for all code merging.

## Quick Reference

```bash
# Run the full Python lint pipeline (format + check + mypy + codespell + deptry)
uv run poe lint

# Run both Python and Flutter linters
uv run poe lint-all

# Run individual tools
uv run poe format       # Ruff auto-format
uv run poe typecheck    # MyPy strict mode
uv run poe spell        # Codespell
uv run poe deptry       # Dependency analysis
uv run poe lint-flutter # Flutter analyze

# Run all pre-commit hooks (includes ruff, codespell, detect-secrets, and more)
uv run poe pre-commit
```

---

## Python Linting

### Ruff (Linter + Formatter)

**Version**: 0.14.14 (pinned in `pyproject.toml` dev dependencies as `ruff==0.14.14`).

Ruff replaces Flake8, isort, Black, pycodestyle, pyflakes, and more in a single high-performance tool.

**Configuration** (from `pyproject.toml`):

```toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "RUF", "D"]
ignore = ["E501", "C901", "D100", "D104"]

[tool.ruff.lint.isort]
known-first-party = ["sre_agent"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.extend-per-file-ignores]
"tests/**" = ["D"]
"eval/**" = ["D"]
"deploy/**" = ["D"]
```

**Rule categories**:

| Code | Category | Description |
|------|----------|-------------|
| `E` | pycodestyle errors | Basic style violations |
| `F` | pyflakes | Undefined names, unused imports |
| `W` | pycodestyle warnings | Style warnings |
| `I` | isort | Import sorting |
| `B` | flake8-bugbear | Common bug patterns |
| `UP` | pyupgrade | Python version upgrade suggestions |
| `RUF` | Ruff-specific | Ruff's own lint rules |
| `D` | pydocstyle | Docstring conventions (Google style) |

**Ignored rules**:

| Code | Reason |
|------|--------|
| `E501` | Line length handled by formatter (88 char limit via `line-length`) |
| `C901` | Complexity checks disabled (some agent logic is inherently complex) |
| `D100` | Missing module-level docstring (not required for every file) |
| `D104` | Missing `__init__.py` docstring (not required) |

**Per-file ignores**: Docstring rules (`D`) are disabled for `tests/`, `eval/`, and `deploy/` directories.

**Poe tasks**:
*   `uv run poe format` -- Runs `ruff format .` (auto-format in place).
*   `uv run poe lint` -- Runs the full sequence: format, `ruff check .`, mypy, codespell, deptry.

### MyPy (Static Type Checking)

**Mode**: Strict.

**Configuration** (from `pyproject.toml`):

```toml
[tool.mypy]
python_version = "3.10"
strict = true
ignore_missing_imports = true
pretty = true
show_error_codes = true
check_untyped_defs = true
disallow_untyped_defs = true
warn_unused_ignores = true
warn_return_any = true
no_implicit_optional = true
exclude = ["tests/", "eval/", "deploy/", "adk-docs/", "adk-python/", "autosre/", "scripts/", "docs/"]
```

**Key enforcement rules**:
*   `disallow_untyped_defs = true` -- Every function must have type annotations.
*   `no_implicit_optional = true` -- Write `name: str | None = None`, not `name: str = None`.
*   `warn_return_any = true` -- Functions returning `Any` are flagged.
*   `strict = true` -- Enables the full suite of strict checks.
*   `ignore_missing_imports = true` -- Allows third-party libraries without type stubs.

**Excluded directories**: Tests, eval, deploy, adk-docs, adk-python, autosre (Flutter), scripts, and docs are not type-checked by MyPy.

**Poe task**: `uv run poe typecheck` -- Runs `mypy .`.

### Codespell (Spelling)

Automated spell checking for code, comments, and documentation.

**Configuration** (from `pyproject.toml`):

```toml
[tool.codespell]
skip = "*.json,*.test.json,*.js,*.lock,./web/node_modules/*,./web/.next/*,./.venv/*,./.git/*,pyproject.toml,./autosre/build/*,./autosre/.dart_tool/*,./adk-docs/*,./adk-python/*,./autosre/linux/*,./autosre/windows/*,./autosre/macos/*"
ignore-words-list = "allReady,ot"
```

**Poe task**: `uv run poe spell` -- Runs `codespell`.

### Deptry (Dependency Analysis)

Detects unused and missing dependencies in `pyproject.toml`.

**Configuration** (from `pyproject.toml`):

```toml
[tool.deptry]
ignore = ["DEP001", "DEP004"]

[tool.deptry.per_rule_ignores]
DEP002 = ["grpcio", "requests", ...]  # Runtime-only deps
DEP003 = ["mcp", "pydantic_core", "proto", "anyio"]  # Transitive deps
```

*   `DEP001` (missing dependency) and `DEP004` (misplaced dev dependency) are globally ignored.
*   Several packages are explicitly allowed in `DEP002` (unused) and `DEP003` (transitive) because they are runtime requirements or re-exported from other packages.

**Poe task**: `uv run poe deptry` -- Runs `deptry .`.

---

## Dart/Flutter Linting

### Dart Analyzer

**Configuration**: `autosre/analysis_options.yaml` (extends `package:flutter_lints/flutter.yaml`).

**Key lint rules** enabled:

| Rule | Purpose |
|------|---------|
| `always_declare_return_types` | Explicit return types on all functions |
| `prefer_single_quotes` | Consistent quoting style |
| `sort_child_properties_last` | Widget tree readability |
| `unawaited_futures` | Catch missing `await` on async calls |
| `avoid_void_async` | Prefer `Future<void>` over `void` for async functions |
| `omit_local_variable_types` | Use `var` / `final` for locals (type inference) |
| `prefer_const_constructors` | Performance: const constructors where possible |
| `prefer_const_declarations` | Const for compile-time constants |
| `prefer_final_fields` | Immutability: final fields where possible |
| `use_key_in_widget_constructors` | Widget identity for efficient rebuilds |

### Enforcement

*   No `info`, `warning`, or `error` level issues allowed in the `lib/` directory.
*   **Poe task**: `uv run poe lint-flutter` -- Runs `flutter analyze` from the `autosre/` directory.

---

## Pre-commit Hooks

Pre-commit hooks run automatically on `git commit` (after `uv run pre-commit install`) or manually via `uv run poe pre-commit`.

**Configuration**: `.pre-commit-config.yaml`

| Hook | Source | Description |
|------|--------|-------------|
| `ruff` | `astral-sh/ruff-pre-commit` (v0.14.13) | Lint with auto-fix (`--fix`) |
| `ruff-format` | `astral-sh/ruff-pre-commit` (v0.14.13) | Auto-format code |
| `check-yaml` | `pre-commit/pre-commit-hooks` (v4.6.0) | Validate YAML syntax |
| `end-of-file-fixer` | `pre-commit/pre-commit-hooks` (v4.6.0) | Ensure files end with newline |
| `trailing-whitespace` | `pre-commit/pre-commit-hooks` (v4.6.0) | Remove trailing whitespace |
| `check-added-large-files` | `pre-commit/pre-commit-hooks` (v4.6.0) | Block files over 1000 KB |
| `codespell` | `codespell-project/codespell` (v2.2.6) | Spelling check |
| `detect-secrets` | `Yelp/detect-secrets` (v1.5.0) | Secret scanning against `.secrets.baseline` |

> [!NOTE]
> The Ruff version in pre-commit (`v0.14.13`) and the pinned dev dependency (`ruff==0.14.14`) may differ slightly. The `pyproject.toml` version is authoritative for CI; the pre-commit hook provides a fast local check.

### Setting Up Pre-commit

```bash
# Install the git hooks (run once after cloning)
uv run pre-commit install

# Run all hooks manually on all files
uv run poe pre-commit

# Or equivalently
uv run pre-commit run --all-files
```

### Secret Scanning (detect-secrets)

The `detect-secrets` hook scans for accidentally committed secrets (API keys, passwords, tokens). It uses a baseline file (`.secrets.baseline`) to track known false positives.

If the hook flags a new secret:
1.  Remove the secret from the code if it is real.
2.  If it is a false positive, update the baseline: `uv run detect-secrets scan --baseline .secrets.baseline`.

---

## Rules for AI Coding Agents

1.  **Lint-First**: After making changes, the first verification step must be `uv run poe lint`.
2.  **Fix Before Review**: Do not ask the user for review if the linter is failing.
3.  **No Suppressions**: Use `noqa` or `type: ignore` only as an absolute last resort. Prefer fixing the architectural issue.
4.  **Zero Tolerance**: Target 0 errors, 0 warnings across all linters.

---

## Lint Pipeline Summary

The `uv run poe lint` task runs these steps in sequence:

1.  `ruff format .` -- Auto-format code.
2.  `ruff check .` -- Lint for errors, style, imports, bugs, docstrings.
3.  `mypy .` -- Static type checking (strict mode).
4.  `codespell` -- Spelling check.
5.  `deptry .` -- Dependency analysis.

The `uv run poe lint-all` task adds:

6.  `flutter analyze` -- Dart/Flutter analysis (from `autosre/` directory).

---
*Last verified: 2026-02-15 -- Auto SRE Team*
