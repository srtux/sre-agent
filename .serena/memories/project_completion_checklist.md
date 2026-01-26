# Project Completion Checklist

Before finishing any task or submitting a PR, ensure the following steps are performed:

1. **Verify Logic**: Manually verify the change works as expected in the targeted environment (Local/Remote).
2. **Linting**: Run `uv run poe lint-all` to ensure zero warnings/errors.
3. **Automated Tests**: Run `uv run poe test-all` for Python and `flutter test` for Dart. All tests must pass.
4. **Coverage**: Ensure code coverage has not dropped below the 80% threshold.
5. **OpenSpec Consistency**: Verify that the implementation matches the behavioral specifications in `openspec/specs/` or its `openspec/changes/` artifact.
6. **Types**: Verify strict MyPy compliance for any new Python code.
6. **Documentation**: Update any relevant `.md` files in `docs/` or the root `PROJECT_PLAN.md` if the architectural context has changed.
7. **Refactoring**: Ensure all Pydantic models follow the `frozen=True, extra="forbid"` rule.
