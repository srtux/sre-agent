import 'dart:convert';

import 'package:autosre/models/adk_schema.dart';
import 'package:autosre/models/time_range.dart';
import 'package:autosre/services/dashboard_state.dart';
import 'package:autosre/services/explorer_query_service.dart';
import 'package:autosre/services/project_service.dart';
import 'package:autosre/widgets/conversation/dashboard_panel_wrapper.dart';
import 'package:autosre/widgets/dashboard/dashboard_panel.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../test_helper.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // ===========================================================================
  // 1. DashboardState defaults
  // ===========================================================================
  group('DashboardState defaults', () {
    late DashboardState state;

    setUp(() {
      state = DashboardState();
    });

    test('default active tab should be logs', () {
      expect(state.activeTab, DashboardDataType.logs);
    });

    test('default active tab should not be traces', () {
      expect(state.activeTab, isNot(DashboardDataType.traces));
    });

    test('default time range should be 15 minutes', () {
      expect(state.timeRange.preset, TimeRangePreset.fifteenMinutes);
    });

    test('default time range minutesAgo should be approximately 15', () {
      // The time range is created dynamically, so allow a small tolerance
      expect(state.timeRange.minutesAgo, closeTo(15, 1));
    });

    test('default time range should not be 1 hour', () {
      expect(state.timeRange.preset, isNot(TimeRangePreset.oneHour));
    });

    test('default time range display label should show 15 minutes', () {
      expect(state.timeRange.displayLabel, 'Last 15 minutes');
    });

    test('time range can be changed from default', () {
      final newRange = TimeRange.fromPreset(TimeRangePreset.oneHour);
      state.setTimeRange(newRange);
      expect(state.timeRange.preset, TimeRangePreset.oneHour);
      expect(state.timeRange.minutesAgo, closeTo(60, 1));
    });

    test('clear does not reset active tab to traces', () {
      state.setActiveTab(DashboardDataType.metrics);
      state.clear();
      // After clear, activeTab is not explicitly reset by clear(),
      // but adding items may auto-set it. Verify it stays as-is.
      expect(state.activeTab, DashboardDataType.metrics);
    });

    test('default dashboard is closed', () {
      expect(state.isOpen, isFalse);
    });

    test('default has no data', () {
      expect(state.hasData, isFalse);
      expect(state.items, isEmpty);
    });
  });

  // ===========================================================================
  // 2. ProjectService needsProjectSelection flag
  // ===========================================================================
  group('ProjectService needsProjectSelection', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('needsProjectSelection should be false initially', () {
      final mockClient = MockClient((request) async {
        return http.Response('{}', 200);
      });
      Future<http.Client> clientFactory() async => mockClient;

      final service = ProjectService.newInstance(clientFactory: clientFactory);
      expect(service.needsProjectSelection.value, isFalse);
      service.dispose();
    });

    test('needsProjectSelection should be true after fetchProjects '
        'completes with no saved project', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path.contains('projects/list')) {
          return http.Response(
            jsonEncode({
              'projects': [
                {'project_id': 'proj-1', 'display_name': 'Project 1'},
                {'project_id': 'proj-2', 'display_name': 'Project 2'},
              ],
            }),
            200,
          );
        }
        if (request.url.path.contains('preferences')) {
          return http.Response('{}', 200);
        }
        if (request.url.path.contains('recent')) {
          return http.Response('{"projects": []}', 200);
        }
        if (request.url.path.contains('starred')) {
          return http.Response('{"projects": []}', 200);
        }
        return http.Response('{}', 200);
      });
      Future<http.Client> clientFactory() async => mockClient;

      final service = ProjectService.newInstance(clientFactory: clientFactory);

      // No saved project in SharedPreferences
      await service.fetchProjects();

      // Since no project was previously saved, needsProjectSelection
      // should be set to true
      expect(service.needsProjectSelection.value, isTrue);
      service.dispose();
    });

    test('needsProjectSelection should remain false when fetchProjects '
        'finds a saved project', () async {
      SharedPreferences.setMockInitialValues({'selected_project_id': 'proj-1'});

      final mockClient = MockClient((request) async {
        if (request.url.path.contains('projects/list')) {
          return http.Response(
            jsonEncode({
              'projects': [
                {'project_id': 'proj-1', 'display_name': 'Project 1'},
              ],
            }),
            200,
          );
        }
        if (request.url.path.contains('recent')) {
          return http.Response('{"projects": []}', 200);
        }
        if (request.url.path.contains('starred')) {
          return http.Response('{"projects": []}', 200);
        }
        return http.Response('{}', 200);
      });
      Future<http.Client> clientFactory() async => mockClient;

      final service = ProjectService.newInstance(clientFactory: clientFactory);
      await service.fetchProjects();

      // Project was found from saved preferences
      expect(service.needsProjectSelection.value, isFalse);
      expect(service.selectedProjectId, 'proj-1');
      service.dispose();
    });

    test('needsProjectSelection should be cleared to false '
        'when selectProjectInstance is called', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path.contains('projects/list')) {
          return http.Response(
            jsonEncode({
              'projects': [
                {'project_id': 'proj-1', 'display_name': 'Project 1'},
              ],
            }),
            200,
          );
        }
        if (request.url.path.contains('preferences')) {
          return http.Response('{}', 200);
        }
        if (request.url.path.contains('recent')) {
          return http.Response('{"projects": []}', 200);
        }
        if (request.url.path.contains('starred')) {
          return http.Response('{"projects": []}', 200);
        }
        return http.Response('{}', 200);
      });
      Future<http.Client> clientFactory() async => mockClient;

      final service = ProjectService.newInstance(clientFactory: clientFactory);

      // Fetch projects with no saved project -> needsProjectSelection = true
      await service.fetchProjects();
      expect(service.needsProjectSelection.value, isTrue);

      // Select a project -> needsProjectSelection should be cleared
      const project = GcpProject(projectId: 'proj-1', displayName: 'Project 1');
      service.selectProjectInstance(project);

      expect(service.needsProjectSelection.value, isFalse);
      expect(service.selectedProjectId, 'proj-1');
      service.dispose();
    });

    test(
      'selectProjectInstance with null still clears needsProjectSelection',
      () async {
        final mockClient = MockClient((request) async {
          if (request.url.path.contains('projects/list')) {
            return http.Response('{"projects": []}', 200);
          }
          if (request.url.path.contains('preferences')) {
            return http.Response('{}', 200);
          }
          if (request.url.path.contains('recent')) {
            return http.Response('{"projects": []}', 200);
          }
          if (request.url.path.contains('starred')) {
            return http.Response('{"projects": []}', 200);
          }
          return http.Response('{}', 200);
        });
        Future<http.Client> clientFactory() async => mockClient;

        final service = ProjectService.newInstance(
          clientFactory: clientFactory,
        );

        await service.fetchProjects();
        expect(service.needsProjectSelection.value, isTrue);

        // Calling selectProjectInstance(null) should still clear the flag
        service.selectProjectInstance(null);
        expect(service.needsProjectSelection.value, isFalse);
        service.dispose();
      },
    );

    test('selectProject (by ID) also clears needsProjectSelection', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path.contains('projects/list')) {
          return http.Response(
            jsonEncode({
              'projects': [
                {'project_id': 'proj-1', 'display_name': 'Project 1'},
              ],
            }),
            200,
          );
        }
        if (request.url.path.contains('preferences')) {
          return http.Response('{}', 200);
        }
        if (request.url.path.contains('recent')) {
          return http.Response('{"projects": []}', 200);
        }
        if (request.url.path.contains('starred')) {
          return http.Response('{"projects": []}', 200);
        }
        return http.Response('{}', 200);
      });
      Future<http.Client> clientFactory() async => mockClient;

      final service = ProjectService.newInstance(clientFactory: clientFactory);

      await service.fetchProjects();
      expect(service.needsProjectSelection.value, isTrue);

      // selectProject calls selectProjectInstance internally
      service.selectProject('proj-1');
      expect(service.needsProjectSelection.value, isFalse);
      expect(service.selectedProjectId, 'proj-1');
      service.dispose();
    });
  });

  // ===========================================================================
  // 3. ExplorerQueryService new methods
  // ===========================================================================
  group('ExplorerQueryService loadDefaultLogs', () {
    late DashboardState dashboardState;

    setUp(() {
      dashboardState = DashboardState();
    });

    test(
      'loadDefaultLogs calls /api/tools/logs/query with minutes_ago=15',
      () async {
        final capturedRequests = <http.Request>[];

        final mockClient = MockClient((request) async {
          capturedRequests.add(request);
          return http.Response(
            jsonEncode({
              'entries': [
                {
                  'insert_id': 'log-1',
                  'timestamp': '2025-01-01T00:00:00Z',
                  'severity': 'INFO',
                  'payload': 'test log',
                },
              ],
            }),
            200,
          );
        });

        final service = ExplorerQueryService(
          dashboardState: dashboardState,
          clientFactory: () async => mockClient,
          baseUrl: 'http://localhost:8001',
        );

        await service.loadDefaultLogs(projectId: 'test-project');

        expect(capturedRequests, isNotEmpty);
        final request = capturedRequests.first;
        expect(request.url.path, '/api/tools/logs/query');

        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['minutes_ago'], 15);
        expect(body['limit'], 100);
        expect(body['filter'], '');
        expect(body['project_id'], 'test-project');
      },
    );

    test('loadDefaultLogs adds log entries to dashboard state', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'entries': [
              {
                'insert_id': 'log-1',
                'timestamp': '2025-01-01T00:00:00Z',
                'severity': 'ERROR',
                'payload': 'error log',
              },
            ],
          }),
          200,
        );
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadDefaultLogs();

      expect(dashboardState.items.length, 1);
      expect(dashboardState.items.first.type, DashboardDataType.logs);
      expect(dashboardState.items.first.source, DataSource.manual);
      // loadDefaultLogs does not open dashboard or set tab; the caller does.
    });

    test('loadDefaultLogs sets loading state correctly', () async {
      final loadingStates = <bool>[];
      dashboardState.addListener(() {
        loadingStates.add(dashboardState.isLoading(DashboardDataType.logs));
      });

      final mockClient = MockClient((request) async {
        return http.Response(jsonEncode({'entries': []}), 200);
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadDefaultLogs();

      // Loading should be false after completion
      expect(dashboardState.isLoading(DashboardDataType.logs), isFalse);
    });

    test('loadDefaultLogs sets error on failure', () async {
      final mockClient = MockClient((request) async {
        return http.Response('Internal Server Error', 500);
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadDefaultLogs();

      expect(dashboardState.errorFor(DashboardDataType.logs), isNotNull);
      expect(dashboardState.isLoading(DashboardDataType.logs), isFalse);
    });

    test('loadDefaultLogs sets last query filter to empty string', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'entries': [
              {
                'insert_id': 'log-1',
                'timestamp': '2025-01-01T00:00:00Z',
                'severity': 'INFO',
                'payload': 'test',
              },
            ],
          }),
          200,
        );
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadDefaultLogs();

      expect(dashboardState.getLastQueryFilter(DashboardDataType.logs), '');
    });
  });

  group('ExplorerQueryService loadSlowTraces', () {
    late DashboardState dashboardState;

    setUp(() {
      dashboardState = DashboardState();
    });

    test(
      'loadSlowTraces calls /api/tools/traces/query with correct params',
      () async {
        final capturedRequests = <http.Request>[];

        final mockClient = MockClient((request) async {
          capturedRequests.add(request);
          return http.Response(
            jsonEncode([
              {
                'trace_id': 'trace-1',
                'spans': [
                  {
                    'span_id': 'span-1',
                    'name': 'slow-op',
                    'start_time': '2025-01-01T00:00:00Z',
                    'end_time': '2025-01-01T00:00:05Z',
                  },
                ],
              },
            ]),
            200,
          );
        });

        final service = ExplorerQueryService(
          dashboardState: dashboardState,
          clientFactory: () async => mockClient,
          baseUrl: 'http://localhost:8001',
        );

        await service.loadSlowTraces(projectId: 'test-project');

        expect(capturedRequests, isNotEmpty);
        final request = capturedRequests.first;
        expect(request.url.path, '/api/tools/traces/query');

        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['filter'], 'MinDuration:3s');
        expect(body['minutes_ago'], 60);
        expect(body['limit'], 20);
        expect(body['project_id'], 'test-project');
      },
    );

    test('loadSlowTraces adds trace data to dashboard state', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {
              'trace_id': 'trace-1',
              'spans': [
                {
                  'span_id': 'span-1',
                  'name': 'slow-op',
                  'start_time': '2025-01-01T00:00:00Z',
                  'end_time': '2025-01-01T00:00:05Z',
                },
              ],
            },
          ]),
          200,
        );
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadSlowTraces();

      expect(dashboardState.items.length, 1);
      expect(dashboardState.items.first.type, DashboardDataType.traces);
      expect(dashboardState.items.first.source, DataSource.manual);
      // loadSlowTraces does not open dashboard or set tab; the caller does.
    });

    test('loadSlowTraces skips traces with empty spans', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {'trace_id': 'trace-empty', 'spans': []},
            {
              'trace_id': 'trace-valid',
              'spans': [
                {
                  'span_id': 'span-1',
                  'name': 'valid-op',
                  'start_time': '2025-01-01T00:00:00Z',
                  'end_time': '2025-01-01T00:00:01Z',
                },
              ],
            },
          ]),
          200,
        );
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadSlowTraces();

      // Only the trace with non-empty spans should be added
      expect(dashboardState.items.length, 1);
      expect(dashboardState.items.first.traceData?.traceId, 'trace-valid');
    });

    test(
      'loadSlowTraces does not open dashboard when no traces found',
      () async {
        final mockClient = MockClient((request) async {
          return http.Response(jsonEncode([]), 200);
        });

        final service = ExplorerQueryService(
          dashboardState: dashboardState,
          clientFactory: () async => mockClient,
          baseUrl: 'http://localhost:8001',
        );

        await service.loadSlowTraces();

        expect(dashboardState.items, isEmpty);
        // Dashboard should not be opened when there are no results
        expect(dashboardState.isOpen, isFalse);
      },
    );

    test('loadSlowTraces sets loading state correctly', () async {
      final mockClient = MockClient((request) async {
        return http.Response(jsonEncode([]), 200);
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadSlowTraces();

      expect(dashboardState.isLoading(DashboardDataType.traces), isFalse);
    });

    test('loadSlowTraces sets error on failure', () async {
      final mockClient = MockClient((request) async {
        return http.Response('Server Error', 500);
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadSlowTraces();

      expect(dashboardState.errorFor(DashboardDataType.traces), isNotNull);
      expect(dashboardState.isLoading(DashboardDataType.traces), isFalse);
    });
  });

  group('ExplorerQueryService loadRecentAlerts', () {
    late DashboardState dashboardState;

    setUp(() {
      dashboardState = DashboardState();
    });

    test(
      'loadRecentAlerts calls /api/tools/alerts/query with minutes_ago=10080',
      () async {
        final capturedRequests = <http.Request>[];

        final mockClient = MockClient((request) async {
          capturedRequests.add(request);
          return http.Response(
            jsonEncode({
              'incident_id': 'inc-1',
              'title': 'Test Alert',
              'start_time': '2025-01-01T00:00:00Z',
              'status': 'resolved',
              'events': [
                {
                  'timestamp': '2025-01-01T00:00:00Z',
                  'type': 'opened',
                  'description': 'Alert opened',
                },
              ],
            }),
            200,
          );
        });

        final service = ExplorerQueryService(
          dashboardState: dashboardState,
          clientFactory: () async => mockClient,
          baseUrl: 'http://localhost:8001',
        );

        await service.loadRecentAlerts(projectId: 'test-project');

        expect(capturedRequests, isNotEmpty);
        final request = capturedRequests.first;
        expect(request.url.path, '/api/tools/alerts/query');

        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['minutes_ago'], 10080); // 7 days in minutes
        expect(body['project_id'], 'test-project');
        // filter is empty string for loadRecentAlerts
        expect(body['filter'], '');
      },
    );

    test('loadRecentAlerts minutes_ago equals 7 days in minutes', () async {
      final capturedRequests = <http.Request>[];

      final mockClient = MockClient((request) async {
        capturedRequests.add(request);
        return http.Response(
          jsonEncode({
            'incident_id': 'inc-1',
            'title': 'Alert',
            'start_time': '2025-01-01T00:00:00Z',
            'status': 'resolved',
            'events': [
              {
                'timestamp': '2025-01-01T00:00:00Z',
                'type': 'opened',
                'description': 'Alert opened',
              },
            ],
          }),
          200,
        );
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadRecentAlerts();

      final body =
          jsonDecode(capturedRequests.first.body) as Map<String, dynamic>;
      // 7 days = 7 * 24 * 60 = 10080 minutes
      expect(body['minutes_ago'], 7 * 24 * 60);
    });

    test('loadRecentAlerts adds alert data to dashboard state', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'incident_id': 'inc-1',
            'title': 'CPU High',
            'start_time': '2025-01-01T00:00:00Z',
            'status': 'open',
            'events': [
              {
                'timestamp': '2025-01-01T00:00:00Z',
                'type': 'opened',
                'description': 'Alert triggered',
              },
            ],
          }),
          200,
        );
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadRecentAlerts();

      expect(dashboardState.items.length, 1);
      expect(dashboardState.items.first.type, DashboardDataType.alerts);
      expect(dashboardState.items.first.source, DataSource.manual);
      // loadRecentAlerts does not open dashboard or set tab; the caller does.
    });

    test('loadRecentAlerts sets loading state correctly', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'incident_id': 'inc-1',
            'title': 'Alert',
            'start_time': '2025-01-01T00:00:00Z',
            'status': 'resolved',
            'events': [],
          }),
          200,
        );
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadRecentAlerts();

      expect(dashboardState.isLoading(DashboardDataType.alerts), isFalse);
    });

    test('loadRecentAlerts sets error on failure', () async {
      final mockClient = MockClient((request) async {
        return http.Response('Gateway Timeout', 504);
      });

      final service = ExplorerQueryService(
        dashboardState: dashboardState,
        clientFactory: () async => mockClient,
        baseUrl: 'http://localhost:8001',
      );

      await service.loadRecentAlerts();

      expect(dashboardState.errorFor(DashboardDataType.alerts), isNotNull);
      expect(dashboardState.isLoading(DashboardDataType.alerts), isFalse);
    });
  });

  // ===========================================================================
  // 4. Dashboard panel width default
  // ===========================================================================
  group('DashboardPanelWrapper default width', () {
    late DashboardState dashboardState;

    setUp(() {
      dashboardState = DashboardState();
    });

    testWidgets('default width factor should be 0.7', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(2000, 800);
      tester.view.devicePixelRatio = 1.0;

      addTearDown(() {
        tester.view.resetPhysicalSize();
      });

      // Open the dashboard so the panel renders
      dashboardState.openDashboard();

      await tester.pumpWidget(
        wrapWithProviders(
          MaterialApp(
            home: Scaffold(
              body: DashboardPanelWrapper(
                dashboardState: dashboardState,
                totalWidth: 2000,
                onPromptRequest: (_) {},
              ),
            ),
          ),
          dashboard: dashboardState,
        ),
      );

      await tester.pumpAndSettle();

      // The DashboardPanelWrapper uses an AnimatedContainer with
      // width = totalWidth * _dashboardWidthFactor (default 0.7)
      // So at 2000px total width, the panel should be 1400px
      final wrapperFinder = find.byType(DashboardPanelWrapper);
      expect(wrapperFinder, findsOneWidget);

      final animatedContainerFinder = find.ancestor(
        of: find.byType(DashboardPanel),
        matching: find.byType(AnimatedContainer),
      );
      expect(animatedContainerFinder, findsOneWidget);

      final size = tester.getSize(animatedContainerFinder);
      expect(
        size.width,
        1400.0,
        reason: 'Dashboard width should be 70% of total width (0.7 factor)',
      );
    });

    testWidgets('default width should not be 0.6 (60%)', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1000, 800);
      tester.view.devicePixelRatio = 1.0;

      addTearDown(() {
        tester.view.resetPhysicalSize();
      });

      dashboardState.openDashboard();

      await tester.pumpWidget(
        wrapWithProviders(
          MaterialApp(
            home: Scaffold(
              body: DashboardPanelWrapper(
                dashboardState: dashboardState,
                totalWidth: 1000,
                isChatOpen: false,
                onPromptRequest: (_) {},
              ),
            ),
          ),
          dashboard: dashboardState,
        ),
      );

      await tester.pumpAndSettle();

      final animatedContainerFinder = find.ancestor(
        of: find.byType(DashboardPanel),
        matching: find.byType(AnimatedContainer),
      );
      final size = tester.getSize(animatedContainerFinder);

      // Should NOT be 600px (which would be 0.6 factor)
      expect(
        size.width,
        isNot(600.0),
        reason: 'Dashboard width should not be 60% (old default)',
      );
    });

    testWidgets('width factor at 1920px screen yields 1344px panel', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1920, 1080);
      tester.view.devicePixelRatio = 1.0;

      addTearDown(() {
        tester.view.resetPhysicalSize();
      });

      dashboardState.openDashboard();

      await tester.pumpWidget(
        wrapWithProviders(
          MaterialApp(
            home: Scaffold(
              body: DashboardPanelWrapper(
                dashboardState: dashboardState,
                totalWidth: 1920,
                onPromptRequest: (_) {},
              ),
            ),
          ),
          dashboard: dashboardState,
        ),
      );

      await tester.pumpAndSettle();

      final animatedContainerFinder = find.ancestor(
        of: find.byType(DashboardPanel),
        matching: find.byType(AnimatedContainer),
      );
      final size = tester.getSize(animatedContainerFinder);

      // 1920 * 0.7 = 1344
      expect(
        size.width,
        1344.0,
        reason: 'Dashboard should be 70% of 1920px = 1344px',
      );
    });

    testWidgets('panel does not render when dashboard is closed', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1000, 800);
      tester.view.devicePixelRatio = 1.0;

      addTearDown(() {
        tester.view.resetPhysicalSize();
      });

      // Dashboard is closed by default
      expect(dashboardState.isOpen, isFalse);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DashboardPanelWrapper(
              dashboardState: dashboardState,
              totalWidth: 1000,
              isChatOpen: false,
              onPromptRequest: (_) {},
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // When closed, it renders SizedBox.shrink
      final animatedContainerFinder = find.byType(AnimatedContainer);
      expect(animatedContainerFinder, findsNothing);
    });
  });

  // ===========================================================================
  // Integration: DashboardState defaults work together
  // ===========================================================================
  group('DashboardState defaults integration', () {
    test('new DashboardState has logs tab and 15-min time range', () {
      final state = DashboardState();

      // Verify both defaults are set together
      expect(state.activeTab, DashboardDataType.logs);
      expect(state.timeRange.preset, TimeRangePreset.fifteenMinutes);
      expect(state.timeRange.minutesAgo, closeTo(15, 1));
    });

    test('adding log data keeps default logs tab', () {
      final state = DashboardState();
      state.addLogEntries(const LogEntriesData(entries: []), 'test', {});

      // Should still be on logs tab
      expect(state.activeTab, DashboardDataType.logs);
    });

    test('addFromEvent with logs category preserves logs active tab', () {
      final state = DashboardState();

      state.addFromEvent({
        'category': 'logs',
        'widget_type': 'x-sre-log-entries-viewer',
        'tool_name': 'fetch_logs',
        'data': {
          'entries': [
            {
              'insert_id': 'log-1',
              'timestamp': '2025-01-01T00:00:00Z',
              'severity': 'INFO',
              'payload': 'test',
            },
          ],
        },
      });

      // Active tab should be set to logs (matching the event category)
      expect(state.activeTab, DashboardDataType.logs);
      expect(state.isOpen, isTrue);
    });

    test('timeRange minutesAgo is usable in ExplorerQueryService', () {
      final state = DashboardState();
      // The default time range should produce a valid minutesAgo value
      // that can be serialized in API payloads
      final minutesAgo = state.timeRange.minutesAgo;
      expect(minutesAgo, greaterThan(0));
      expect(minutesAgo, lessThanOrEqualTo(15));
    });
  });
}
