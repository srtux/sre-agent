import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/services/connectivity_service.dart';

void main() {
  late ConnectivityService service;

  setUp(() {
    // Use a fresh internal instance via mock pattern
    service = ConnectivityService();
    ConnectivityService.mockInstance = service;
  });

  tearDown(() {
    ConnectivityService.mockInstance = null;
  });

  group('ConnectivityService', () {
    test('initial status is unknown', () {
      // Create a direct internal instance to test initial state
      final freshService = ConnectivityService();
      ConnectivityService.mockInstance = freshService;
      expect(freshService.status.value, ConnectivityStatus.unknown);
      ConnectivityService.mockInstance = null;
    });

    test('updateStatus sets connected', () {
      service.updateStatus(true);
      expect(service.status.value, ConnectivityStatus.connected);
    });

    test('updateStatus sets offline', () {
      service.updateStatus(false);
      expect(service.status.value, ConnectivityStatus.offline);
    });

    test('updateStatus notifies listeners on change', () {
      var notifyCount = 0;
      service.addListener(() => notifyCount++);

      service.updateStatus(true);
      expect(notifyCount, 1);

      service.updateStatus(false);
      expect(notifyCount, 2);
    });

    test('updateStatus does not notify when status unchanged', () {
      var notifyCount = 0;
      service.updateStatus(true);
      service.addListener(() => notifyCount++);

      // Set to same value
      service.updateStatus(true);
      expect(notifyCount, 0);
    });

    test('singleton returns same instance', () {
      ConnectivityService.mockInstance = service;
      expect(ConnectivityService.instance, same(service));
    });

    test('factory constructor returns instance', () {
      ConnectivityService.mockInstance = service;
      final fromFactory = ConnectivityService();
      expect(fromFactory, same(service));
    });

    test('status is a ValueListenable', () {
      expect(service.status, isA<ValueListenable<ConnectivityStatus>>());
    });
  });

  group('ConnectivityStatus enum', () {
    test('has all expected values', () {
      expect(ConnectivityStatus.values, contains(ConnectivityStatus.connected));
      expect(ConnectivityStatus.values, contains(ConnectivityStatus.offline));
      expect(ConnectivityStatus.values, contains(ConnectivityStatus.unknown));
      expect(ConnectivityStatus.values.length, 3);
    });
  });
}
