# 🧪 Frontend Testing Guide (Flutter)

The SRE Agent frontend features a comprehensive test suite that ensures UI stability, responsive layout behavior, and correct service interaction.

## 🏗️ The Testing Architecture

We use a **Provider-based Injection** pattern to enable hermetic testing. Instead of widgets accessing singletons directly, they consume services from the `BuildContext`.

### Key Utility: `test_helper.dart`

To simplify test setup, all tests should use the `wrapWithProviders` utility located in `autosre/test/test_helper.dart`.

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

## 🛠️ Testing Patterns

### 1. Mocking Services
Every service in `lib/services/` has a corresponding mock in `test_helper.dart` (e.g., `MockAuthService`, `MockProjectService`). These mocks:
- Implement the service interface.
- Use `ValueNotifier` for reactive state (loading, errors).
- Stub async methods (fetch, sign-in) to return immediately or provide mock data.

### 2. Layout Verification
For responsive components (like the Dashboard resize handle), tests must enforce specific physical sizes:

```dart
testWidgets('Dashboard expands', (tester) async {
  tester.view.physicalSize = const Size(1920, 1080);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);

  // ... test ...
});
```

### 3. Authentication States
Verify the `AuthWrapper` behavior by injecting different authenticated states into `MockAuthService`:

```dart
final mockAuth = MockAuthService(authenticated: false);
await tester.pumpWidget(wrapWithProviders(const AuthWrapper(), auth: mockAuth));
expect(find.byType(LoginPage), findsOneWidget);
```

## 🚀 Execution

Run the frontend test suite from the repository root:
```bash
uv run poe test-flutter
```

Or from the `autosre/` directory:
```bash
flutter test
```

## ✅ Best Practices
1.  **Use `pumpAndSettle()`**: When testing animations or transitions (like opening the dashboard), always use `pumpAndSettle()` to wait for the UI to stabilize.
2.  **Verify via Icons/Tooltips**: Use `find.byIcon()` or `find.byTooltip()` for interactive elements to ensure accessibility standards are met.
3.  **Clean Up**: Always call `clearMockSingletons()` in `tearDown` if your test modifies global service instances.
