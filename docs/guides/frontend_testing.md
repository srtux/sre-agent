# Frontend Testing Guide (Flutter)

The SRE Agent frontend features a comprehensive test suite with **21 test files** containing approximately **112 tests** that ensure UI stability, responsive layout behavior, and correct service interaction.

## Test Suite Structure

```text
autosre/test/
├── test_helper.dart                         # Shared mocks and wrapWithProviders utility
├── ansi_parser_test.dart                    # ANSI escape code parsing
├── auth_guest_login_test.dart               # Guest login flow
├── auth_service_helper_test.dart            # Auth service helper utilities
├── auth_service_logic_test.dart             # Auth service business logic
├── auth_wrapper_test.dart                   # AuthWrapper widget routing
├── catalog_renderer_test.dart               # Catalog rendering components
├── component_wrapper_test.dart              # Component wrapper widgets
├── conversation_page_test.dart              # Main conversation page
├── council_panel_test.dart                  # Council panel dashboard (51 tests)
├── dashboard_layout_test.dart               # Dashboard layout and structure
├── dashboard_resize_test.dart               # Dashboard resize handle behavior
├── glow_action_chip_test.dart               # GlowActionChip widget
├── glow_action_chip_scroll_test.dart        # GlowActionChip scroll behavior
├── help_service_test.dart                   # Help service logic
├── prompt_history_service_test.dart         # Prompt history persistence
├── services_test.dart                       # Service integration tests
├── unified_prompt_input_test.dart           # Prompt input widget
├── unified_prompt_input_functional_test.dart # Prompt input functional behavior
├── widget_test.dart                         # Basic widget smoke test
├── pages/
│   └── help_page_test.dart                  # Help page widget tests
└── widgets/
    └── trace_waterfall_test.dart            # Trace waterfall visualization
```

## The Testing Architecture

We use a **Provider-based Injection** pattern to enable hermetic testing. Instead of widgets accessing singletons directly, they consume services from the `BuildContext`. Additionally, a **singleton mock** mechanism allows non-widget code to use the same mock instances.

### Key Utility: `test_helper.dart`

All tests should use the utilities in `autosre/test/test_helper.dart`. This file provides:

1. **Mock service classes** -- one for each service in `lib/services/`
2. **`wrapWithProviders()`** -- wraps a widget tree with all required `Provider` instances
3. **`setupMockSingletons()` / `clearMockSingletons()`** -- sets/clears static mock instances for non-widget code paths

### Available Mock Services

| Mock Class | Real Service | Key Behavior |
|-----------|-------------|-------------|
| `MockAuthService` | `AuthService` | Configurable `authenticated` state, implements `ChangeNotifier` |
| `MockProjectService` | `ProjectService` | Returns empty project lists, no-op operations |
| `MockSessionService` | `SessionService` | Returns empty session lists, no-op CRUD operations |
| `MockToolConfigService` | `ToolConfigService` | Returns empty tool configs, no-op enable/disable |
| `MockPromptHistoryService` | `PromptHistoryService` | Returns empty history, no-op add |
| `MockConnectivityService` | `ConnectivityService` | Always returns `ConnectivityStatus.connected` |
| `MockADKContentGenerator` | `ADKContentGenerator` | Exposes broadcast `StreamController`s for simulating events (tool calls, text, UI messages, dashboard, suggestions) |

### Basic Test Setup

```dart
import 'test_helper.dart';

void main() {
  testWidgets('My Widget Test', (tester) async {
    await tester.pumpWidget(
      wrapWithProviders(
        const MaterialApp(home: MyWidget()),
        auth: MockAuthService(authenticated: true),
        project: MockProjectService(),
      ),
    );

    // ... assertions ...
  });
}
```

The `wrapWithProviders` function accepts optional overrides for each service. Unspecified services default to their mock implementations. It also calls `setupMockSingletons()` internally, so singleton-based code paths also use the mock instances.

## Testing Patterns

### 1. Mocking Services
Every service in `lib/services/` has a corresponding mock in `test_helper.dart`. These mocks:
- Implement the service interface.
- Use `ValueNotifier` for reactive state (loading, errors, data lists).
- Stub async methods (fetch, sign-in) to return immediately or provide mock data.
- Are injectable both via `Provider` (for widget code) and via static `mockInstance` (for non-widget code).

### 2. Mocking the ADK Content Generator
For testing chat and streaming behavior, use `MockADKContentGenerator`:

```dart
final mockGenerator = MockADKContentGenerator();

// Simulate a tool call event
mockGenerator.emitToolCall({'type': 'dashboard', 'panel': 'traces'});

// Simulate text response
mockGenerator.emitText('Investigation complete.');

// Simulate processing state
mockGenerator.setProcessing(true);
```

### 3. Layout Verification
For responsive components (like the Dashboard resize handle), tests must enforce specific physical sizes:

```dart
testWidgets('Dashboard expands', (tester) async {
  tester.view.physicalSize = const Size(1920, 1080);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);

  // ... test ...
});
```

### 4. Authentication States
Verify the `AuthWrapper` behavior by injecting different authenticated states into `MockAuthService`:

```dart
final mockAuth = MockAuthService(authenticated: false);
await tester.pumpWidget(wrapWithProviders(const AuthWrapper(), auth: mockAuth));
expect(find.byType(LoginPage), findsOneWidget);
```

### 5. Singleton Cleanup
When tests modify global service instances via `setupMockSingletons()`, always clean up:

```dart
tearDown(() {
  clearMockSingletons();
});
```

## Execution

Run the frontend test suite from the repository root:
```bash
uv run poe test-flutter
```

Or from the `autosre/` directory:
```bash
flutter test
```

Run a specific test file:
```bash
cd autosre && flutter test test/council_panel_test.dart
```

Run both backend and frontend tests together:
```bash
uv run poe test-all
```

## Best Practices

1. **Use `pumpAndSettle()`**: When testing animations or transitions (like opening the dashboard), always use `pumpAndSettle()` to wait for the UI to stabilize.
2. **Verify via Icons/Tooltips**: Use `find.byIcon()` or `find.byTooltip()` for interactive elements to ensure accessibility standards are met.
3. **Clean Up**: Always call `clearMockSingletons()` in `tearDown` if your test modifies global service instances.
4. **Use `wrapWithProviders`**: Never manually set up providers in tests. Always use the shared utility to ensure consistency and avoid missing dependencies.
5. **Test File Naming**: Flutter test files use the `<name>_test.dart` convention (not `test_<name>.dart` as in Python).

---
*Last verified: 2026-02-15 -- Auto SRE Team*
