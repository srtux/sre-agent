import 'package:flutter/foundation.dart';

/// Enum representing the application's connectivity status.
enum ConnectivityStatus { connected, offline, unknown }

/// A service that monitors and provides the application's connectivity status.
class ConnectivityService extends ChangeNotifier {
  static ConnectivityService? _mockInstance;
  static ConnectivityService get instance => _mockInstance ?? _internalInstance;
  static final ConnectivityService _internalInstance =
      ConnectivityService._internal();

  factory ConnectivityService() => instance;

  @visibleForTesting
  static set mockInstance(ConnectivityService? mock) => _mockInstance = mock;

  ConnectivityService._internal();

  final ValueNotifier<ConnectivityStatus> _status = ValueNotifier(
    ConnectivityStatus.unknown,
  );

  /// The current connectivity status.
  ValueListenable<ConnectivityStatus> get status => _status;

  /// Updates the connectivity status.
  ///
  /// This should be called by the component that directly handles the connection
  /// (e.g., ADKContentGenerator).
  void updateStatus(bool isConnected) {
    final newStatus = isConnected
        ? ConnectivityStatus.connected
        : ConnectivityStatus.offline;
    if (_status.value != newStatus) {
      // Setting .value already fires ValueNotifier listeners; calling
      // notifyListeners() on top of that caused a redundant rebuild cycle.
      _status.value = newStatus;
    }
  }

  @override
  void dispose() {
    _status.dispose();
    super.dispose();
  }
}
