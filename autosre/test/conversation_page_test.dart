import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/pages/conversation_page.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'test_helper.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
  });

  tearDown(() {
    clearMockSingletons();
  });

  testWidgets('ConversationPage builds correctly and shows logo', (
    WidgetTester tester,
  ) async {
    // Set a desktop-like size
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(
      wrapWithProviders(const MaterialApp(home: ConversationPage())),
    );

    // Initial pump
    await tester.pumpAndSettle();

    // Verify logo icon - it's Icons.smart_toy (robot)
    expect(find.byIcon(Icons.smart_toy), findsAtLeast(1));

    // Verify input area elements
    expect(find.byType(TextField), findsAtLeast(1));
    expect(find.text('Ask anything...'), findsOneWidget);
  });
}
