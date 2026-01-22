import 'package:flutter/foundation.dart';

/// Enum representing the application's connectivity status.
enum ConnectivityStatus { connected, offline, unknown }

/// A service that monitors and provides the application's connectivity status.
class ConnectivityService extends ChangeNotifier {
  static final ConnectivityService _instance = ConnectivityService._internal();
  factory ConnectivityService() => _instance;
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
      _status.value = newStatus;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _status.dispose();
    super.dispose();
  }
}
