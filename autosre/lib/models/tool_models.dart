import 'package:flutter/foundation.dart';

/// A log entry for a tool invocation (running, completed, or error).
class ToolLog {
  final String toolName;
  final Map<String, dynamic> args;
  final String status; // 'running', 'completed', 'error'
  final String? result;
  final String? timestamp;
  final String? duration;

  ToolLog({
    required this.toolName,
    required this.args,
    required this.status,
    this.result,
    this.timestamp,
    this.duration,
  });

  factory ToolLog.fromJson(Map<String, dynamic> json) {
    return ToolLog(
      toolName: json['tool_name'] as String? ?? '',
      args: Map<String, dynamic>.from(json['args'] as Map? ?? {}),
      status: json['status'] as String? ?? 'unknown',
      result: json['result']?.toString(),
      timestamp: json['timestamp'] as String?,
      duration: json['duration'] as String?,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ToolLog &&
          runtimeType == other.runtimeType &&
          toolName == other.toolName &&
          mapEquals(args, other.args) &&
          status == other.status &&
          result == other.result &&
          timestamp == other.timestamp &&
          duration == other.duration;

  @override
  int get hashCode =>
      Object.hash(toolName, status, result, timestamp, duration);
}
