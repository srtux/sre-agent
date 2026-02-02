
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/widgets/dashboard/dashboard_panel.dart';
import 'package:autosre/pages/conversation_page.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'test_helper.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  tearDown(() {
    clearMockSingletons();
  });

  testWidgets('Dashboard opens and is resizable', (WidgetTester tester) async {
    // Set desktop size
    tester.view.physicalSize = const Size(1920, 1080);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(
      wrapWithProviders(
        const MaterialApp(
          home: ConversationPage(),
        ),
      ),
    );

    // Initial pump
    await tester.pumpAndSettle();

    // 1. Open Dashboard
    final toggleFinder = find.byTooltip('Open Investigation Dashboard');
    expect(toggleFinder, findsOneWidget);
    await tester.tap(toggleFinder);
    await tester.pumpAndSettle();

    // 2. Find Resize Handle
    final handleFinder = find.byKey(const Key('dashboard_resize_handle'));
    expect(handleFinder, findsOneWidget);

    // 3. Find DashboardPanel
    final dashboardFinder = find.byType(DashboardPanel);
    expect(dashboardFinder, findsOneWidget);

    // Initial width should be 60% of 1920 = 1152
    final initialSize = tester.getSize(find.ancestor(of: dashboardFinder, matching: find.byType(SizedBox)).first);
    expect(initialSize.width, 1152.0);

    // Drag handle to the LEFT by 192 (10% of width)
    // New width should be 70% of 1920 = 1344
    await tester.drag(handleFinder, const Offset(-192.0, 0));
    await tester.pump();

    final expandedSize = tester.getSize(find.ancestor(of: dashboardFinder, matching: find.byType(SizedBox)).first);
    expect(expandedSize.width, 1344.0);
  });
}
