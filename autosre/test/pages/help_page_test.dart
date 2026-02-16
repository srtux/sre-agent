import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/pages/help_page.dart';
import 'package:autosre/services/help_service.dart';

class MockHelpService extends HelpService {
  MockHelpService() : super.newInstance();

  @override
  Future<List<HelpTopic>> fetchTopics() async {
    return [
      HelpTopic(
        id: 'traces',
        title: 'Traces & Spans',
        description: 'Understand request flows.',
        icon: Icons.timeline,
        categories: ['Observability'],
        contentFile: 'traces.md',
      ),
      HelpTopic(
        id: 'circuit_breaker',
        title: 'Circuit Breakers',
        description: 'Protecting resources.',
        icon: Icons.electric_bolt,
        categories: ['Analysis'],
        contentFile: 'circuit_breaker.md',
      ),
      HelpTopic(
        id: 'rca',
        title: 'Root Cause Analysis',
        description: 'Detective work.',
        icon: Icons.psychology,
        categories: ['Analysis'],
        contentFile: 'rca.md',
      ),
    ];
  }

  @override
  Future<String> fetchContent(String topicId) async {
    if (topicId == 'traces') {
      return '### Getting Started with Traces\nContent here.';
    }
    return 'Default mock content';
  }
}

void main() {
  setUp(() {
    HelpService.mockInstance = MockHelpService();
  });

  tearDown(() {
    HelpService.mockInstance = null;
  });

  Widget createWidgetUnderTest() {
    return const MaterialApp(home: HelpPage());
  }

  testWidgets('HelpPage renders correctly with mock data', (
    WidgetTester tester,
  ) async {
    // Set a consistent surface size for tests
    await tester.binding.setSurfaceSize(const Size(1200, 1000));

    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    // Verify Title
    expect(find.text('AutoSRE Help'), findsWidgets);
    expect(
      find.textContaining('documentation for the modern SRE'),
      findsOneWidget,
    );

    // Verify Categories
    expect(find.byKey(const ValueKey('category_All')), findsOneWidget);
    expect(
      find.byKey(const ValueKey('category_Observability')),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('category_Analysis')), findsOneWidget);

    // Verify first topic is visible
    expect(find.text('Traces & Spans'), findsOneWidget);

    await tester.binding.setSurfaceSize(null);
  });

  testWidgets('Search filters topics', (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1200, 1000));
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    expect(find.text('Traces & Spans'), findsOneWidget);

    // Search for "Circuit"
    await tester.enterText(find.byType(TextField), 'Circuit');
    await tester.pumpAndSettle();

    expect(find.text('Traces & Spans'), findsNothing);
    expect(find.text('Circuit Breakers'), findsOneWidget);

    await tester.binding.setSurfaceSize(null);
  });

  testWidgets('Category selection filters topics', (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1200, 1000));
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    // Select "Analysis" category via key
    await tester.tap(find.byKey(const ValueKey('category_Analysis')));
    await tester.pumpAndSettle();

    expect(find.text('Root Cause Analysis'), findsOneWidget);
    expect(find.text('Traces & Spans'), findsNothing);

    await tester.binding.setSurfaceSize(null);
  });

  testWidgets('HelpCard fetches content on tap', (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1200, 1000));
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    // Find the 'traces' help card via key
    final cardFinder = find.byKey(const ValueKey('topic_traces'));
    expect(cardFinder, findsOneWidget);

    // Verify expanded content is NOT visible initially
    expect(find.textContaining('Getting Started'), findsNothing);

    // Tap to expand
    await tester.tap(cardFinder);
    await tester.pumpAndSettle(const Duration(milliseconds: 500));

    // Expanded content should be visible now
    expect(find.textContaining('Getting Started with Traces'), findsWidgets);

    await tester.binding.setSurfaceSize(null);
  });
}
