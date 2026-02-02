import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/services/help_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  group('HelpService', () {
    test('fetchTopics returns list of HelpTopic', () async {
      final mockData = [
        {
          'id': 'test-id',
          'title': 'Test Title',
          'description': 'Test Desc',
          'icon': 'timeline',
          'categories': ['FAQ'],
          'content_file': 'test.md'
        }
      ];

      final mockClient = MockClient((request) async {
        return http.Response(jsonEncode(mockData), 200);
      });

      final service = HelpService.newInstance(clientFactory: () async => mockClient);
      final topics = await service.fetchTopics();

      expect(topics.length, 1);
      expect(topics.first.id, 'test-id');
      expect(topics.first.title, 'Test Title');
    });

    test('fetchContent returns markdown and caches result', () async {
      var callCount = 0;
      final mockClient = MockClient((request) async {
        callCount++;
        return http.Response('## Mock Content', 200);
      });

      final service = HelpService.newInstance(clientFactory: () async => mockClient);

      // First call
      final content1 = await service.fetchContent('test-id');
      expect(content1, '## Mock Content');
      expect(callCount, 1);

      // Second call (should be cached)
      final content2 = await service.fetchContent('test-id');
      expect(content2, '## Mock Content');
      expect(callCount, 1);
    });

    test('HelpTopic.fromJson handles missing categories', () {
      final json = {
        'id': 'test',
        'title': 'title',
        'description': 'desc',
        'icon': 'article',
        'content_file': 'file.md'
      };

      final topic = HelpTopic.fromJson(json);
      expect(topic.categories, isEmpty);
    });
  });
}
