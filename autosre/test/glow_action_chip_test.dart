import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/widgets/glow_action_chip.dart';

void main() {
  testWidgets('GlowActionChip simple build test', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: GlowActionChip(
              label: 'Test Chip',
              onTap: () {},
              icon: Icons.bolt,
            ),
          ),
        ),
      ),
    );

    expect(find.text('Test Chip'), findsOneWidget);
    expect(find.byIcon(Icons.bolt), findsOneWidget);
  });
}
