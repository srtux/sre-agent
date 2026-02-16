import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/widgets/glow_action_chip.dart';

void main() {
  testWidgets('Multiple GlowActionChips in a horizontal ListView', (
    WidgetTester tester,
  ) async {
    // Narrow window to force overflow
    tester.view.physicalSize = const Size(300, 600);
    tester.view.devicePixelRatio = 1.0;

    final suggestions = List.generate(10, (i) => 'Suggestion $i');

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Column(
            children: [
              SizedBox(
                height: 50,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: suggestions.length,
                  separatorBuilder: (context, index) =>
                      const SizedBox(width: 8),
                  itemBuilder: (context, index) =>
                      GlowActionChip(label: suggestions[index], onTap: () {}),
                ),
              ),
            ],
          ),
        ),
      ),
    );

    // Initial check - should see first few
    expect(find.text('Suggestion 0'), findsOneWidget);
    expect(find.text('Suggestion 9'), findsNothing); // Should be offscreen

    // Scroll until the last item is visible
    final lastItem = find.text('Suggestion 9');
    await tester.dragUntilVisible(
      lastItem,
      find.byType(ListView),
      const Offset(-100, 0),
    );
    await tester.pumpAndSettle();

    // Check last items
    expect(lastItem, findsOneWidget);

    addTearDown(tester.view.resetPhysicalSize);
  });
}
