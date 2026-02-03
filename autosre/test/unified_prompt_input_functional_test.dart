import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/widgets/unified_prompt_input.dart';

void main() {
  group('UnifiedPromptInput Functionality Tests', () {
    late TextEditingController controller;
    late FocusNode focusNode;
    var sendCalled = false;
    var cancelCalled = false;

    setUp(() {
      controller = TextEditingController();
      focusNode = FocusNode();
      sendCalled = false;
      cancelCalled = false;
    });

    tearDown(() {
      controller.dispose();
      focusNode.dispose();
    });

    testWidgets('renders with placeholder text', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: UnifiedPromptInput(
              controller: controller,
              focusNode: focusNode,
              onSend: () => sendCalled = true,
              onCancel: () => cancelCalled = true,
              isProcessing: false,
            ),
          ),
        ),
      );

      expect(find.text('Ask anything...'), findsOneWidget);
      expect(find.byIcon(Icons.arrow_upward_rounded), findsOneWidget);
    });

    testWidgets('calls onSend when text submitted without shift', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: UnifiedPromptInput(
              controller: controller,
              focusNode: focusNode,
              onSend: () => sendCalled = true,
              onCancel: () => cancelCalled = true,
              isProcessing: false,
            ),
          ),
        ),
      );

      await tester.enterText(find.byType(TextField), 'test message');
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pump();

      expect(sendCalled, isTrue);
    });

    testWidgets('shows stop button when processing', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: UnifiedPromptInput(
              controller: controller,
              focusNode: focusNode,
              onSend: () => sendCalled = true,
              onCancel: () => cancelCalled = true,
              isProcessing: true,
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.stop_rounded), findsOneWidget);
      expect(find.byIcon(Icons.arrow_upward_rounded), findsNothing);
    });

    testWidgets('calls onCancel when stop button tapped', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: UnifiedPromptInput(
              controller: controller,
              focusNode: focusNode,
              onSend: () => sendCalled = true,
              onCancel: () => cancelCalled = true,
              isProcessing: true,
            ),
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.stop_rounded));
      await tester.pump();

      expect(cancelCalled, isTrue);
    });

    testWidgets('expands for multi-line input', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: UnifiedPromptInput(
              controller: controller,
              focusNode: focusNode,
              onSend: () => sendCalled = true,
              onCancel: () => cancelCalled = true,
              isProcessing: false,
            ),
          ),
        ),
      );

      // Initial height should be minimum
      final initialHeight = tester
          .getSize(find.byType(UnifiedPromptInput))
          .height;

      await tester.enterText(
        find.byType(TextField),
        'Line 1\nLine 2\nLine 3\nLine 4',
      );
      await tester.pump();

      // Height should increase for multi-line
      final multiLineHeight = tester
          .getSize(find.byType(UnifiedPromptInput))
          .height;
      expect(multiLineHeight, greaterThan(initialHeight));
    });

    testWidgets('focuses text field when container tapped', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: UnifiedPromptInput(
              controller: controller,
              focusNode: focusNode,
              onSend: () => sendCalled = true,
              onCancel: () => cancelCalled = true,
              isProcessing: false,
            ),
          ),
        ),
      );

      expect(focusNode.hasFocus, isFalse);

      await tester.tap(find.byType(UnifiedPromptInput));
      await tester.pump();

      expect(focusNode.hasFocus, isTrue);
    });

    testWidgets('has proper accessibility labels', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: UnifiedPromptInput(
              controller: controller,
              focusNode: focusNode,
              onSend: () => sendCalled = true,
              onCancel: () => cancelCalled = true,
              isProcessing: false,
            ),
          ),
        ),
      );

      // Check for tooltip on send button
      expect(find.byType(Tooltip), findsOneWidget);
    });
  });
}
