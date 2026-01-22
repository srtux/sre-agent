import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:autosre/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('end-to-end test', () {
    testWidgets('tap on the floating action button, verify counter', (
      tester,
    ) async {
      app.main();
      await tester.pumpAndSettle();

      // Verify app title in AppBar
      expect(find.text('AutoSRE'), findsOneWidget);

      // Verify empty state title
      expect(find.text('SRE Assistant'), findsOneWidget);
    });
  });
}
