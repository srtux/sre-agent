# Suggested Commands

## Environment Management
- `uv run poe sync`: Synchronize dependencies.
- `uv pip install <package>`: Install a new package.

## Development Loop
- `uv run poe run`: Start the FastAPI backend server.
- `uv run poe lint-all`: Run all Python linters (Ruff, MyPy, Codespell, etc.).
- `uv run poe test-all`: Run all backend tests.
- `flutter run -d chrome`: Start the Flutter web app (from `autosre/`).

## Testing & Verification
- `uv run pytest <path>`: Run specific tests.
- `uv run pytest --cov=sre_agent`: Check code coverage.
- `flutter analyze`: Catch Dart/Flutter issues.
- `flutter test`: Run frontend unit/widget tests.

## Other Utils
- `ast-grep`: Use for structural search/replace (e.g., `ast-grep run --pattern 'class $NAME(BaseModel): $$$' --lang python`).
- `rg` (ripgrep): Faster searching across files.
- `git status`, `git diff`: standard version control.
