import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/widgets/unified_prompt_input.dart';

void main() {
  testWidgets('UnifiedPromptInput golden test - empty state', (
    WidgetTester tester,
  ) async {
    final controller = TextEditingController();
    final focusNode = FocusNode();

    await tester.pumpWidget(
      MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: ThemeData.dark(),
        home: Scaffold(
          backgroundColor:
              Colors.black, // Dark background to see the component clearly
          body: Center(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
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
      ),
    );

    await tester.pumpAndSettle();

    await expectLater(
      find.byType(UnifiedPromptInput),
      matchesGoldenFile('unified_prompt_input_empty.png'),
    );
  });

  testWidgets('UnifiedPromptInput golden test - multi-line state', (
    WidgetTester tester,
  ) async {
    final controller = TextEditingController();
    final focusNode = FocusNode();

    await tester.pumpWidget(
      MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: ThemeData.dark(),
        home: Scaffold(
          backgroundColor: Colors.black,
          body: Center(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
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
      ),
    );

    // Enter multi-line text
    await tester.enterText(
      find.byType(TextField),
      'Line 1\nLine 2\nLine 3\nLine 4',
    );
    await tester.pump();

    await expectLater(
      find.byType(UnifiedPromptInput),
      matchesGoldenFile('unified_prompt_input_multiline.png'),
    );
  });
}
