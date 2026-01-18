import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/services/project_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  group('ProjectService', () {
    // Mock client that returns success for everything
    final mockClient = MockClient((request) async {
      if (request.url.path.contains('preferences')) {
        return http.Response('{}', 200);
      }
      return http.Response('[]', 200);
    });

    final clientFactory = () async => mockClient;

    test('should initialize with empty projects', () {
      final service = ProjectService.newInstance(clientFactory: clientFactory);
      expect(service.projects.value, isEmpty);
      expect(service.selectedProjectId, isNull);
      service.dispose();
    });

    test('should select project not in list', () {
      final service = ProjectService.newInstance(clientFactory: clientFactory);
      service.selectProject('test-project-123');
      expect(service.selectedProjectId, 'test-project-123');
      service.dispose();
    });

    test('should clear project selection', () {
      final service = ProjectService.newInstance(clientFactory: clientFactory);
      final testProject = GcpProject(
        projectId: 'test-project-123',
        displayName: 'Test Project',
      );
      service.selectProjectInstance(testProject);
      expect(service.selectedProjectId, 'test-project-123');

      service.clearSelection();
      expect(service.selectedProjectId, isNull);
      service.dispose();
    });
  });

  group('GcpProject', () {
    test('model with all fields', () {
      final project = GcpProject(
        projectId: 'test-project-123',
        displayName: 'Test Project',
        projectNumber: '123456789',
      );

      expect(project.projectId, 'test-project-123');
      expect(project.displayName, 'Test Project');
      expect(project.projectNumber, '123456789');
      expect(project.name, 'Test Project');
    });

    test('model without display name', () {
      final project = GcpProject(projectId: 'test-project-123');

      expect(project.name, 'test-project-123');
    });

    test('serialization and deserialization', () {
      final project = GcpProject(
        projectId: 'test-project-123',
        displayName: 'Test Project',
        projectNumber: '123456789',
      );

      final json = project.toJson();
      expect(json['project_id'], 'test-project-123');
      expect(json['display_name'], 'Test Project');
      expect(json['project_number'], '123456789');

      final deserialized = GcpProject.fromJson(json);
      expect(deserialized.projectId, 'test-project-123');
      expect(deserialized.displayName, 'Test Project');
      expect(deserialized.projectNumber, '123456789');
    });
  });
}
