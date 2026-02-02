import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'auth_service.dart';

class PromptHistoryService {
  static const int _maxHistorySize = 50;
  static const String _keyPrefix = 'prompt_history_';

  static PromptHistoryService? _mockInstance;
  static PromptHistoryService get instance => _mockInstance ?? _internalInstance;
  static final PromptHistoryService _internalInstance =
      PromptHistoryService._internal();

  factory PromptHistoryService() => instance;

  @visibleForTesting
  static set mockInstance(PromptHistoryService? mock) => _mockInstance = mock;

  PromptHistoryService._internal();

  /// Save a prompt to the history for the current user
  Future<void> addPrompt(String prompt) async {
    if (prompt.trim().isEmpty) return;

    final user = AuthService.instance.currentUser;
    if (user == null) return;

    final key = '$_keyPrefix${user.email}';
    final prefs = await SharedPreferences.getInstance();

    // Get existing history
    var history = prefs.getStringList(key) ?? [];

    // Remove existing entry to avoid duplicates (move to end)
    history.removeWhere((item) => item == prompt);

    // Add to end (most recent)
    history.add(prompt);

    // Enforce size limit
    if (history.length > _maxHistorySize) {
      history = history.sublist(history.length - _maxHistorySize);
    }

    await prefs.setStringList(key, history);
  }

  /// Get the full history for the current user (oldest first)
  Future<List<String>> getHistory() async {
    final user = AuthService.instance.currentUser;
    if (user == null) return [];

    final key = '$_keyPrefix${user.email}';
    final prefs = await SharedPreferences.getInstance();
    return prefs.getStringList(key) ?? [];
  }
}
