import 'package:flutter/foundation.dart';

/// A single event in an incident timeline.
final class TimelineEvent {
  final String id;
  final DateTime timestamp;
  final String
  type; // 'alert', 'deployment', 'config_change', 'scaling', 'incident', 'recovery', 'agent_action'
  final String title;
  final String? description;
  final String severity; // 'critical', 'high', 'medium', 'low', 'info'
  final Map<String, dynamic>? metadata;
  final bool isCorrelatedToIncident;

  TimelineEvent({
    required this.id,
    required this.timestamp,
    required this.type,
    required this.title,
    this.description,
    this.severity = 'info',
    this.metadata,
    this.isCorrelatedToIncident = false,
  });

  factory TimelineEvent.fromJson(Map<String, dynamic> json) {
    final ts = DateTime.tryParse(json['timestamp']?.toString() ?? '') ??
        DateTime.now();
    return TimelineEvent(
      id: json['id'] as String? ?? '',
      timestamp: ts,
      type: json['type'] as String? ?? 'info',
      title: json['title'] as String? ?? '',
      description: json['description'] as String?,
      severity: json['severity'] as String? ?? 'info',
      metadata: json['metadata'] is Map
          ? Map<String, dynamic>.from(json['metadata'] as Map)
          : null,
      isCorrelatedToIncident: json['is_correlated'] as bool? ?? false,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is TimelineEvent &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          timestamp == other.timestamp &&
          type == other.type &&
          title == other.title &&
          description == other.description &&
          severity == other.severity &&
          mapEquals(metadata, other.metadata) &&
          isCorrelatedToIncident == other.isCorrelatedToIncident;

  @override
  int get hashCode => Object.hash(
    id,
    timestamp,
    type,
    title,
    description,
    severity,
    isCorrelatedToIncident,
  );
}

/// Container for an incident timeline with events and metadata.
final class IncidentTimelineData {
  final String incidentId;
  final String title;
  final DateTime startTime;
  final DateTime? endTime;
  final String status; // 'ongoing', 'mitigated', 'resolved'
  final List<TimelineEvent> events;
  final String? rootCause;
  final Duration? timeToDetect;
  final Duration? timeToMitigate;

  IncidentTimelineData({
    required this.incidentId,
    required this.title,
    required this.startTime,
    this.endTime,
    required this.status,
    required this.events,
    this.rootCause,
    this.timeToDetect,
    this.timeToMitigate,
  });

  factory IncidentTimelineData.fromJson(Map<String, dynamic> json) {
    final startTs = DateTime.tryParse(json['start_time']?.toString() ?? '') ??
        DateTime.now();
    final endTs = DateTime.tryParse(json['end_time']?.toString() ?? '');
    return IncidentTimelineData(
      incidentId: json['incident_id'] as String? ?? '',
      title: json['title'] as String? ?? 'Incident',
      startTime: startTs,
      endTime: endTs,
      status: json['status'] as String? ?? 'ongoing',
      events: (json['events'] as List? ?? [])
          .whereType<Map>()
          .map((e) => TimelineEvent.fromJson(Map<String, dynamic>.from(e)))
          .toList(),
      rootCause: json['root_cause'] as String?,
      timeToDetect: json['ttd_seconds'] != null
          ? Duration(seconds: (json['ttd_seconds'] as num).toInt())
          : null,
      timeToMitigate: json['ttm_seconds'] != null
          ? Duration(seconds: (json['ttm_seconds'] as num).toInt())
          : null,
    );
  }

  IncidentTimelineData copyWith({
    String? incidentId,
    String? title,
    DateTime? startTime,
    DateTime? endTime,
    String? status,
    List<TimelineEvent>? events,
    String? rootCause,
    Duration? timeToDetect,
    Duration? timeToMitigate,
  }) {
    return IncidentTimelineData(
      incidentId: incidentId ?? this.incidentId,
      title: title ?? this.title,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      status: status ?? this.status,
      events: events ?? this.events,
      rootCause: rootCause ?? this.rootCause,
      timeToDetect: timeToDetect ?? this.timeToDetect,
      timeToMitigate: timeToMitigate ?? this.timeToMitigate,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'incident_id': incidentId,
      'title': title,
      'start_time': startTime.toIso8601String(),
      'end_time': endTime?.toIso8601String(),
      'status': status,
      'events': events.map((e) => {
        'id': e.id,
        'timestamp': e.timestamp.toIso8601String(),
        'type': e.type,
        'title': e.title,
        'description': e.description,
        'severity': e.severity,
        'metadata': e.metadata,
        'is_correlated': e.isCorrelatedToIncident,
      }).toList(),
      'root_cause': rootCause,
      'ttd_seconds': timeToDetect?.inSeconds,
      'ttm_seconds': timeToMitigate?.inSeconds,
    };
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is IncidentTimelineData &&
          runtimeType == other.runtimeType &&
          incidentId == other.incidentId &&
          title == other.title &&
          startTime == other.startTime &&
          endTime == other.endTime &&
          status == other.status &&
          listEquals(events, other.events) &&
          rootCause == other.rootCause &&
          timeToDetect == other.timeToDetect &&
          timeToMitigate == other.timeToMitigate;

  @override
  int get hashCode => Object.hash(
    incidentId,
    title,
    startTime,
    endTime,
    status,
    events.length,
    rootCause,
    timeToDetect,
    timeToMitigate,
  );
}
