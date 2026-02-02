
import 'package:autosre/app.dart';
import 'package:autosre/pages/conversation_page.dart';
import 'package:autosre/pages/login_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'test_helper.dart';

void main() {
  testWidgets('AuthWrapper shows ConversationPage when authenticated (bypass mode)', (WidgetTester tester) async {
    final mockAuth = MockAuthService(authenticated: true);

    await tester.pumpWidget(
      wrapWithProviders(
        const MaterialApp(home: AuthWrapper()),
        auth: mockAuth,
      ),
    );

    await tester.pump();

    expect(find.byType(ConversationPage), findsOneWidget);
    expect(find.byType(LoginPage), findsNothing);
  });

  testWidgets('AuthWrapper shows LoginPage when NOT authenticated', (WidgetTester tester) async {
    final mockAuth = MockAuthService(authenticated: false);

    await tester.pumpWidget(
      wrapWithProviders(
        const MaterialApp(home: AuthWrapper()),
        auth: mockAuth,
      ),
    );

    await tester.pump();

    expect(find.byType(LoginPage), findsOneWidget);
    expect(find.byType(ConversationPage), findsNothing);
  });
}
