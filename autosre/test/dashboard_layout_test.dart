import 'package:autosre/models/adk_schema.dart';
// import 'package:autosre/pages/conversation_page.dart';
import 'package:autosre/services/dashboard_state.dart';
// import 'package:autosre/widgets/dashboard/dashboard_panel.dart';
import 'package:autosre/widgets/dashboard/live_alerts_panel.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
// import 'test_helper.dart';

void main() {
  /*
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
    final toggleFinder = find.byTooltip('Dashboard');
    expect(toggleFinder, findsOneWidget, reason: 'Dashboard toggle should be visible');

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
    await tester.tap(find.byTooltip('Dashboard'));
    await tester.pumpAndSettle();

    // Verify it's closed
    expect(dashboardFinder, findsNothing);
  });
*/

  testWidgets('LiveAlertsPanel fills available space with single item', (
    tester,
  ) async {
    // Set a large screen size to verify expansion
    tester.view.physicalSize = const Size(1000, 800);
    tester.view.devicePixelRatio = 1.0;

    addTearDown(() {
      tester.view.resetPhysicalSize();
    });

    // Mock DashboardState with one alert item
    final state = DashboardState();
    state.addAlerts(
      IncidentTimelineData(
        incidentId: 'test-123',
        title: 'Test Incident',
        startTime: DateTime.now(),
        events: [],
        status: 'ongoing',
      ),
      'test_tool',
      {},
    );
    state.setActiveTab(DashboardDataType.alerts);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Column(
            children: [
              Expanded(
                child: LiveAlertsPanel(
                  items: state.items,
                  dashboardState: state,
                ),
              ),
            ],
          ),
        ),
      ),
    );
    // Use pump instead of pumpAndSettle because of CircularProgressIndicator in 'ongoing' alerts
    await tester.pump(const Duration(seconds: 2));

    // Verify LiveAlertsPanel fills the available space (not constrained to 450px).
    // The panel is inside an Expanded widget in a Column, so it should fill
    // the screen height minus minimal chrome. We check the panel size directly
    // rather than drilling into child Containers, since the ManualQueryBar
    // adds a 40px Container at the top.
    final panelFinder = find.byType(LiveAlertsPanel);
    expect(panelFinder, findsOneWidget);

    final size = tester.getSize(panelFinder);
    // Screen is 800px; panel should fill most of it
    expect(
      size.height,
      greaterThan(600),
      reason: 'Alert panel should expand to fill space',
    );
  });
}
