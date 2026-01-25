# World-Class Linting Strategy: The SRE Agent Way

We enforce a "Zero Broken Windows" policy. Linting is not a suggestion; it is a hard requirement for all code merging.

## 🐍 Python: Modern, Fast, and Strict

We use a modern toolchain for Python to ensure maximum quality with minimum overhead.

### Tools
- **Ruff**: The high-performance Python linter and formatter. Replaces Flake8, Isort, Black, and more.
- **MyPy**: Static type checking for Python. We use **Strict Mode**.
- **Codespell**: Automated spell checking to prevent embarrassing typos in documentation and comments.
- **Deptry**: Dependency analysis to prevent unused or missing dependencies in `pyproject.toml`.

### Enforcement
- All linters must pass clean (`uv run poe lint`).
- **Target**: 0 errors, 0 warnings.
- **Rules**:
    - **Google Convention** for docstrings.
    - **Strict Type Checking**: Every function must have type hints. `Any` is discouraged and must be justified.
    - **Sort Imports** automatically via Ruff.

---

## 🎯 Dart/Flutter: High Precision

We follow the official Flutter recommendations but add extra guards for production stability.

### Tools
- **Dart Analyzer**: Integrated linting via `flutter analyze`.
- **Custom Lint Rules**: Defined in `autosre/analysis_options.yaml`.

### Enforcement
- No `info`, `warning`, or `error` level issues allowed in the `lib/` directory.
- **Rules**:
    - **Mandatory Const**: Use `const` constructors wherever possible for widget performance.
    - **Strict Raw Types**: Avoid raw types for collections.
    - **Privacy by Default**: Use `_` for class members that don't need external exposure.

---

## 🤖 Rules for AI Coding Agents

1. **Lint-First**: After making changes, the first tool call **MUST** be `uv run poe lint`.
2. **Fix Before Review**: Do not ask the user for review if the linter is failing.
3. **No Suppressions**: Use `noqa` or `ignore` only as an absolute last resort. Prefer fixing the architectural issue.
