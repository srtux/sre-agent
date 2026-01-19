import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/widgets/unified_prompt_input.dart';

void main() {
  testWidgets('UnifiedPromptInput supports multi-line input', (WidgetTester tester) async {
    final controller = TextEditingController();
    final focusNode = FocusNode();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: UnifiedPromptInput(
              controller: controller,
              focusNode: focusNode,
              onSend: () {},
              onCancel: () {},
              isProcessing: false,
            ),
          ),
        ),
      ),
    );

    // Initial check
    expect(find.byType(TextField), findsOneWidget);
    final textField = tester.widget<TextField>(find.byType(TextField));
    expect(textField.maxLines, 6);
    expect(textField.minLines, 1);
    expect(textField.keyboardType, TextInputType.multiline);

    // Enter single line text
    await tester.enterText(find.byType(TextField), 'Hello');
    await tester.pump();

    // Get initial size
    final initialSize = tester.getSize(find.byType(UnifiedPromptInput));
    expect(initialSize.height, greaterThanOrEqualTo(60));

    // Enter multi-line text
    await tester.enterText(find.byType(TextField), 'Line 1\nLine 2\nLine 3');
    await tester.pump();

    // Verify text is set
    expect(controller.text, 'Line 1\nLine 2\nLine 3');

    // Note: Exact layout size checks can be flaky due to font rendering,
    // but we verified the properties `maxLines` and `keyboardType`.
  });
}
