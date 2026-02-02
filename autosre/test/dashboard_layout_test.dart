
import 'package:autosre/pages/conversation_page.dart';
import 'package:autosre/widgets/dashboard/dashboard_panel.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'test_helper.dart';

void main() {
  testWidgets('DashboardPanel expands to 60% width when toggled', (tester) async {
    // Set a fixed screen size for calculation verification (e.g., 1000px wide)
    tester.view.physicalSize = const Size(1000, 800);
    tester.view.devicePixelRatio = 1.0;

    // Reset visibility before test
    addTearDown(() {
      tester.view.resetPhysicalSize();
      clearMockSingletons();
    });

    await tester.pumpWidget(
      wrapWithProviders(
        const MaterialApp(
          home: ConversationPage(),
        ),
      ),
    );

    // Initial pump to settle animations/init
    await tester.pumpAndSettle();

    // Verify ConversationPage is rendered
    expect(find.byType(ConversationPage), findsOneWidget);

    // Initial State: Dashboard is closed
    final toggleFinder = find.byIcon(Icons.space_dashboard_outlined);
    expect(toggleFinder, findsOneWidget, reason: 'Dashboard toggle should be visible (outlined icon)');

    // Tap to open
    await tester.tap(toggleFinder);
    await tester.pumpAndSettle();

    // Verify DashboardPanel is present
    final dashboardFinder = find.byType(DashboardPanel);
    expect(dashboardFinder, findsOneWidget);

    // Verify Width: Should be 600px (60% of 1000)
    final containerFinder = find.ancestor(
      of: dashboardFinder,
      matching: find.byType(SizedBox),
    ).first;

    final containerSize = tester.getSize(containerFinder);
    expect(containerSize.width, 600.0, reason: 'Dashboard should be 60% of screen width');

    // Tap to close
    await tester.tap(find.byIcon(Icons.space_dashboard_rounded));
    await tester.pumpAndSettle();

    // Verify it's closed
    expect(dashboardFinder, findsNothing);
  });
}
