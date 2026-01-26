# Style and Conventions

## Python (Backend)
- **Pydantic**: ALL models must use `model_config = ConfigDict(frozen=True, extra="forbid")`. Always check the schema before using or modifying.
- **Types**: Strict type hints are required for all functions and fields. Use `str | None` for optional types.
- **Imports**: Prefer absolute imports for cross-module or relative for siblings.
- **Docstrings**: Required for all public functions, following the standard Google style or similar.
- **Tooling**: Use the `@adk_tool` decorator for all agent tools. Tools should return JSON strings following the success/error pattern.
- **Auth**: Respect End-User Credentials (EUC) and Project ID enforcement patterns. NEVER hardcode IDs.

## Flutter (Frontend)
- **Best Practices**: Use `const` where possible, follow standard Flutter project structure.
- **Visuals**: No generic "MVP" looks. Every UI component must look premium and professional.

## General
- **Naming**: `snake_case` for Python, `camelCase` for Dart/JS.
- **Async**: Heavy use of `async/await` for both backend and frontend.
- **BDD (Behavior Driven Development)**: Use OpenSpec for all new features. Define behavior in `openspec/changes/` before implementation. Existing core behavior is documented in `openspec/specs/`.
