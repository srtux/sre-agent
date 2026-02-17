// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'local_database.dart';

// ignore_for_file: type=lint
class $CachedMetricsTable extends CachedMetrics
    with TableInfo<$CachedMetricsTable, CachedMetric> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedMetricsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _metricNameMeta = const VerificationMeta(
    'metricName',
  );
  @override
  late final GeneratedColumn<String> metricName = GeneratedColumn<String>(
    'metric_name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _timestampMeta = const VerificationMeta(
    'timestamp',
  );
  @override
  late final GeneratedColumn<DateTime> timestamp = GeneratedColumn<DateTime>(
    'timestamp',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _valueMeta = const VerificationMeta('value');
  @override
  late final GeneratedColumn<double> value = GeneratedColumn<double>(
    'value',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _projectIdMeta = const VerificationMeta(
    'projectId',
  );
  @override
  late final GeneratedColumn<String> projectId = GeneratedColumn<String>(
    'project_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    metricName,
    timestamp,
    value,
    projectId,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_metrics';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedMetric> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('metric_name')) {
      context.handle(
        _metricNameMeta,
        metricName.isAcceptableOrUnknown(data['metric_name']!, _metricNameMeta),
      );
    } else if (isInserting) {
      context.missing(_metricNameMeta);
    }
    if (data.containsKey('timestamp')) {
      context.handle(
        _timestampMeta,
        timestamp.isAcceptableOrUnknown(data['timestamp']!, _timestampMeta),
      );
    } else if (isInserting) {
      context.missing(_timestampMeta);
    }
    if (data.containsKey('value')) {
      context.handle(
        _valueMeta,
        value.isAcceptableOrUnknown(data['value']!, _valueMeta),
      );
    } else if (isInserting) {
      context.missing(_valueMeta);
    }
    if (data.containsKey('project_id')) {
      context.handle(
        _projectIdMeta,
        projectId.isAcceptableOrUnknown(data['project_id']!, _projectIdMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  CachedMetric map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedMetric(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      metricName: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}metric_name'],
      )!,
      timestamp: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}timestamp'],
      )!,
      value: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}value'],
      )!,
      projectId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}project_id'],
      ),
    );
  }

  @override
  $CachedMetricsTable createAlias(String alias) {
    return $CachedMetricsTable(attachedDatabase, alias);
  }
}

class CachedMetric extends DataClass implements Insertable<CachedMetric> {
  final int id;
  final String metricName;
  final DateTime timestamp;
  final double value;
  final String? projectId;
  const CachedMetric({
    required this.id,
    required this.metricName,
    required this.timestamp,
    required this.value,
    this.projectId,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['metric_name'] = Variable<String>(metricName);
    map['timestamp'] = Variable<DateTime>(timestamp);
    map['value'] = Variable<double>(value);
    if (!nullToAbsent || projectId != null) {
      map['project_id'] = Variable<String>(projectId);
    }
    return map;
  }

  CachedMetricsCompanion toCompanion(bool nullToAbsent) {
    return CachedMetricsCompanion(
      id: Value(id),
      metricName: Value(metricName),
      timestamp: Value(timestamp),
      value: Value(value),
      projectId: projectId == null && nullToAbsent
          ? const Value.absent()
          : Value(projectId),
    );
  }

  factory CachedMetric.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedMetric(
      id: serializer.fromJson<int>(json['id']),
      metricName: serializer.fromJson<String>(json['metricName']),
      timestamp: serializer.fromJson<DateTime>(json['timestamp']),
      value: serializer.fromJson<double>(json['value']),
      projectId: serializer.fromJson<String?>(json['projectId']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'metricName': serializer.toJson<String>(metricName),
      'timestamp': serializer.toJson<DateTime>(timestamp),
      'value': serializer.toJson<double>(value),
      'projectId': serializer.toJson<String?>(projectId),
    };
  }

  CachedMetric copyWith({
    int? id,
    String? metricName,
    DateTime? timestamp,
    double? value,
    Value<String?> projectId = const Value.absent(),
  }) => CachedMetric(
    id: id ?? this.id,
    metricName: metricName ?? this.metricName,
    timestamp: timestamp ?? this.timestamp,
    value: value ?? this.value,
    projectId: projectId.present ? projectId.value : this.projectId,
  );
  CachedMetric copyWithCompanion(CachedMetricsCompanion data) {
    return CachedMetric(
      id: data.id.present ? data.id.value : this.id,
      metricName: data.metricName.present
          ? data.metricName.value
          : this.metricName,
      timestamp: data.timestamp.present ? data.timestamp.value : this.timestamp,
      value: data.value.present ? data.value.value : this.value,
      projectId: data.projectId.present ? data.projectId.value : this.projectId,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedMetric(')
          ..write('id: $id, ')
          ..write('metricName: $metricName, ')
          ..write('timestamp: $timestamp, ')
          ..write('value: $value, ')
          ..write('projectId: $projectId')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, metricName, timestamp, value, projectId);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedMetric &&
          other.id == this.id &&
          other.metricName == this.metricName &&
          other.timestamp == this.timestamp &&
          other.value == this.value &&
          other.projectId == this.projectId);
}

class CachedMetricsCompanion extends UpdateCompanion<CachedMetric> {
  final Value<int> id;
  final Value<String> metricName;
  final Value<DateTime> timestamp;
  final Value<double> value;
  final Value<String?> projectId;
  const CachedMetricsCompanion({
    this.id = const Value.absent(),
    this.metricName = const Value.absent(),
    this.timestamp = const Value.absent(),
    this.value = const Value.absent(),
    this.projectId = const Value.absent(),
  });
  CachedMetricsCompanion.insert({
    this.id = const Value.absent(),
    required String metricName,
    required DateTime timestamp,
    required double value,
    this.projectId = const Value.absent(),
  }) : metricName = Value(metricName),
       timestamp = Value(timestamp),
       value = Value(value);
  static Insertable<CachedMetric> custom({
    Expression<int>? id,
    Expression<String>? metricName,
    Expression<DateTime>? timestamp,
    Expression<double>? value,
    Expression<String>? projectId,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (metricName != null) 'metric_name': metricName,
      if (timestamp != null) 'timestamp': timestamp,
      if (value != null) 'value': value,
      if (projectId != null) 'project_id': projectId,
    });
  }

  CachedMetricsCompanion copyWith({
    Value<int>? id,
    Value<String>? metricName,
    Value<DateTime>? timestamp,
    Value<double>? value,
    Value<String?>? projectId,
  }) {
    return CachedMetricsCompanion(
      id: id ?? this.id,
      metricName: metricName ?? this.metricName,
      timestamp: timestamp ?? this.timestamp,
      value: value ?? this.value,
      projectId: projectId ?? this.projectId,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (metricName.present) {
      map['metric_name'] = Variable<String>(metricName.value);
    }
    if (timestamp.present) {
      map['timestamp'] = Variable<DateTime>(timestamp.value);
    }
    if (value.present) {
      map['value'] = Variable<double>(value.value);
    }
    if (projectId.present) {
      map['project_id'] = Variable<String>(projectId.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedMetricsCompanion(')
          ..write('id: $id, ')
          ..write('metricName: $metricName, ')
          ..write('timestamp: $timestamp, ')
          ..write('value: $value, ')
          ..write('projectId: $projectId')
          ..write(')'))
        .toString();
  }
}

class $CachedLogsTable extends CachedLogs
    with TableInfo<$CachedLogsTable, CachedLog> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedLogsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _timestampMeta = const VerificationMeta(
    'timestamp',
  );
  @override
  late final GeneratedColumn<DateTime> timestamp = GeneratedColumn<DateTime>(
    'timestamp',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _severityMeta = const VerificationMeta(
    'severity',
  );
  @override
  late final GeneratedColumn<String> severity = GeneratedColumn<String>(
    'severity',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _messageMeta = const VerificationMeta(
    'message',
  );
  @override
  late final GeneratedColumn<String> message = GeneratedColumn<String>(
    'message',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _projectIdMeta = const VerificationMeta(
    'projectId',
  );
  @override
  late final GeneratedColumn<String> projectId = GeneratedColumn<String>(
    'project_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    timestamp,
    severity,
    message,
    projectId,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_logs';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedLog> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('timestamp')) {
      context.handle(
        _timestampMeta,
        timestamp.isAcceptableOrUnknown(data['timestamp']!, _timestampMeta),
      );
    } else if (isInserting) {
      context.missing(_timestampMeta);
    }
    if (data.containsKey('severity')) {
      context.handle(
        _severityMeta,
        severity.isAcceptableOrUnknown(data['severity']!, _severityMeta),
      );
    } else if (isInserting) {
      context.missing(_severityMeta);
    }
    if (data.containsKey('message')) {
      context.handle(
        _messageMeta,
        message.isAcceptableOrUnknown(data['message']!, _messageMeta),
      );
    } else if (isInserting) {
      context.missing(_messageMeta);
    }
    if (data.containsKey('project_id')) {
      context.handle(
        _projectIdMeta,
        projectId.isAcceptableOrUnknown(data['project_id']!, _projectIdMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  CachedLog map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedLog(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      timestamp: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}timestamp'],
      )!,
      severity: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}severity'],
      )!,
      message: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}message'],
      )!,
      projectId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}project_id'],
      ),
    );
  }

  @override
  $CachedLogsTable createAlias(String alias) {
    return $CachedLogsTable(attachedDatabase, alias);
  }
}

class CachedLog extends DataClass implements Insertable<CachedLog> {
  final String id;
  final DateTime timestamp;
  final String severity;
  final String message;
  final String? projectId;
  const CachedLog({
    required this.id,
    required this.timestamp,
    required this.severity,
    required this.message,
    this.projectId,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['timestamp'] = Variable<DateTime>(timestamp);
    map['severity'] = Variable<String>(severity);
    map['message'] = Variable<String>(message);
    if (!nullToAbsent || projectId != null) {
      map['project_id'] = Variable<String>(projectId);
    }
    return map;
  }

  CachedLogsCompanion toCompanion(bool nullToAbsent) {
    return CachedLogsCompanion(
      id: Value(id),
      timestamp: Value(timestamp),
      severity: Value(severity),
      message: Value(message),
      projectId: projectId == null && nullToAbsent
          ? const Value.absent()
          : Value(projectId),
    );
  }

  factory CachedLog.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedLog(
      id: serializer.fromJson<String>(json['id']),
      timestamp: serializer.fromJson<DateTime>(json['timestamp']),
      severity: serializer.fromJson<String>(json['severity']),
      message: serializer.fromJson<String>(json['message']),
      projectId: serializer.fromJson<String?>(json['projectId']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'timestamp': serializer.toJson<DateTime>(timestamp),
      'severity': serializer.toJson<String>(severity),
      'message': serializer.toJson<String>(message),
      'projectId': serializer.toJson<String?>(projectId),
    };
  }

  CachedLog copyWith({
    String? id,
    DateTime? timestamp,
    String? severity,
    String? message,
    Value<String?> projectId = const Value.absent(),
  }) => CachedLog(
    id: id ?? this.id,
    timestamp: timestamp ?? this.timestamp,
    severity: severity ?? this.severity,
    message: message ?? this.message,
    projectId: projectId.present ? projectId.value : this.projectId,
  );
  CachedLog copyWithCompanion(CachedLogsCompanion data) {
    return CachedLog(
      id: data.id.present ? data.id.value : this.id,
      timestamp: data.timestamp.present ? data.timestamp.value : this.timestamp,
      severity: data.severity.present ? data.severity.value : this.severity,
      message: data.message.present ? data.message.value : this.message,
      projectId: data.projectId.present ? data.projectId.value : this.projectId,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedLog(')
          ..write('id: $id, ')
          ..write('timestamp: $timestamp, ')
          ..write('severity: $severity, ')
          ..write('message: $message, ')
          ..write('projectId: $projectId')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, timestamp, severity, message, projectId);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedLog &&
          other.id == this.id &&
          other.timestamp == this.timestamp &&
          other.severity == this.severity &&
          other.message == this.message &&
          other.projectId == this.projectId);
}

class CachedLogsCompanion extends UpdateCompanion<CachedLog> {
  final Value<String> id;
  final Value<DateTime> timestamp;
  final Value<String> severity;
  final Value<String> message;
  final Value<String?> projectId;
  final Value<int> rowid;
  const CachedLogsCompanion({
    this.id = const Value.absent(),
    this.timestamp = const Value.absent(),
    this.severity = const Value.absent(),
    this.message = const Value.absent(),
    this.projectId = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CachedLogsCompanion.insert({
    required String id,
    required DateTime timestamp,
    required String severity,
    required String message,
    this.projectId = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       timestamp = Value(timestamp),
       severity = Value(severity),
       message = Value(message);
  static Insertable<CachedLog> custom({
    Expression<String>? id,
    Expression<DateTime>? timestamp,
    Expression<String>? severity,
    Expression<String>? message,
    Expression<String>? projectId,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (timestamp != null) 'timestamp': timestamp,
      if (severity != null) 'severity': severity,
      if (message != null) 'message': message,
      if (projectId != null) 'project_id': projectId,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CachedLogsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? timestamp,
    Value<String>? severity,
    Value<String>? message,
    Value<String?>? projectId,
    Value<int>? rowid,
  }) {
    return CachedLogsCompanion(
      id: id ?? this.id,
      timestamp: timestamp ?? this.timestamp,
      severity: severity ?? this.severity,
      message: message ?? this.message,
      projectId: projectId ?? this.projectId,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (timestamp.present) {
      map['timestamp'] = Variable<DateTime>(timestamp.value);
    }
    if (severity.present) {
      map['severity'] = Variable<String>(severity.value);
    }
    if (message.present) {
      map['message'] = Variable<String>(message.value);
    }
    if (projectId.present) {
      map['project_id'] = Variable<String>(projectId.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedLogsCompanion(')
          ..write('id: $id, ')
          ..write('timestamp: $timestamp, ')
          ..write('severity: $severity, ')
          ..write('message: $message, ')
          ..write('projectId: $projectId, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $CachedMetricsTable cachedMetrics = $CachedMetricsTable(this);
  late final $CachedLogsTable cachedLogs = $CachedLogsTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    cachedMetrics,
    cachedLogs,
  ];
}

typedef $$CachedMetricsTableCreateCompanionBuilder =
    CachedMetricsCompanion Function({
      Value<int> id,
      required String metricName,
      required DateTime timestamp,
      required double value,
      Value<String?> projectId,
    });
typedef $$CachedMetricsTableUpdateCompanionBuilder =
    CachedMetricsCompanion Function({
      Value<int> id,
      Value<String> metricName,
      Value<DateTime> timestamp,
      Value<double> value,
      Value<String?> projectId,
    });

class $$CachedMetricsTableFilterComposer
    extends Composer<_$AppDatabase, $CachedMetricsTable> {
  $$CachedMetricsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get metricName => $composableBuilder(
    column: $table.metricName,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get timestamp => $composableBuilder(
    column: $table.timestamp,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get value => $composableBuilder(
    column: $table.value,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get projectId => $composableBuilder(
    column: $table.projectId,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedMetricsTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedMetricsTable> {
  $$CachedMetricsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get metricName => $composableBuilder(
    column: $table.metricName,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get timestamp => $composableBuilder(
    column: $table.timestamp,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get value => $composableBuilder(
    column: $table.value,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get projectId => $composableBuilder(
    column: $table.projectId,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedMetricsTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedMetricsTable> {
  $$CachedMetricsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get metricName => $composableBuilder(
    column: $table.metricName,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get timestamp =>
      $composableBuilder(column: $table.timestamp, builder: (column) => column);

  GeneratedColumn<double> get value =>
      $composableBuilder(column: $table.value, builder: (column) => column);

  GeneratedColumn<String> get projectId =>
      $composableBuilder(column: $table.projectId, builder: (column) => column);
}

class $$CachedMetricsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedMetricsTable,
          CachedMetric,
          $$CachedMetricsTableFilterComposer,
          $$CachedMetricsTableOrderingComposer,
          $$CachedMetricsTableAnnotationComposer,
          $$CachedMetricsTableCreateCompanionBuilder,
          $$CachedMetricsTableUpdateCompanionBuilder,
          (
            CachedMetric,
            BaseReferences<_$AppDatabase, $CachedMetricsTable, CachedMetric>,
          ),
          CachedMetric,
          PrefetchHooks Function()
        > {
  $$CachedMetricsTableTableManager(_$AppDatabase db, $CachedMetricsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedMetricsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedMetricsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedMetricsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> metricName = const Value.absent(),
                Value<DateTime> timestamp = const Value.absent(),
                Value<double> value = const Value.absent(),
                Value<String?> projectId = const Value.absent(),
              }) => CachedMetricsCompanion(
                id: id,
                metricName: metricName,
                timestamp: timestamp,
                value: value,
                projectId: projectId,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String metricName,
                required DateTime timestamp,
                required double value,
                Value<String?> projectId = const Value.absent(),
              }) => CachedMetricsCompanion.insert(
                id: id,
                metricName: metricName,
                timestamp: timestamp,
                value: value,
                projectId: projectId,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedMetricsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedMetricsTable,
      CachedMetric,
      $$CachedMetricsTableFilterComposer,
      $$CachedMetricsTableOrderingComposer,
      $$CachedMetricsTableAnnotationComposer,
      $$CachedMetricsTableCreateCompanionBuilder,
      $$CachedMetricsTableUpdateCompanionBuilder,
      (
        CachedMetric,
        BaseReferences<_$AppDatabase, $CachedMetricsTable, CachedMetric>,
      ),
      CachedMetric,
      PrefetchHooks Function()
    >;
typedef $$CachedLogsTableCreateCompanionBuilder =
    CachedLogsCompanion Function({
      required String id,
      required DateTime timestamp,
      required String severity,
      required String message,
      Value<String?> projectId,
      Value<int> rowid,
    });
typedef $$CachedLogsTableUpdateCompanionBuilder =
    CachedLogsCompanion Function({
      Value<String> id,
      Value<DateTime> timestamp,
      Value<String> severity,
      Value<String> message,
      Value<String?> projectId,
      Value<int> rowid,
    });

class $$CachedLogsTableFilterComposer
    extends Composer<_$AppDatabase, $CachedLogsTable> {
  $$CachedLogsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get timestamp => $composableBuilder(
    column: $table.timestamp,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get severity => $composableBuilder(
    column: $table.severity,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get message => $composableBuilder(
    column: $table.message,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get projectId => $composableBuilder(
    column: $table.projectId,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedLogsTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedLogsTable> {
  $$CachedLogsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get timestamp => $composableBuilder(
    column: $table.timestamp,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get severity => $composableBuilder(
    column: $table.severity,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get message => $composableBuilder(
    column: $table.message,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get projectId => $composableBuilder(
    column: $table.projectId,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedLogsTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedLogsTable> {
  $$CachedLogsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<DateTime> get timestamp =>
      $composableBuilder(column: $table.timestamp, builder: (column) => column);

  GeneratedColumn<String> get severity =>
      $composableBuilder(column: $table.severity, builder: (column) => column);

  GeneratedColumn<String> get message =>
      $composableBuilder(column: $table.message, builder: (column) => column);

  GeneratedColumn<String> get projectId =>
      $composableBuilder(column: $table.projectId, builder: (column) => column);
}

class $$CachedLogsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedLogsTable,
          CachedLog,
          $$CachedLogsTableFilterComposer,
          $$CachedLogsTableOrderingComposer,
          $$CachedLogsTableAnnotationComposer,
          $$CachedLogsTableCreateCompanionBuilder,
          $$CachedLogsTableUpdateCompanionBuilder,
          (
            CachedLog,
            BaseReferences<_$AppDatabase, $CachedLogsTable, CachedLog>,
          ),
          CachedLog,
          PrefetchHooks Function()
        > {
  $$CachedLogsTableTableManager(_$AppDatabase db, $CachedLogsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedLogsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedLogsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedLogsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<DateTime> timestamp = const Value.absent(),
                Value<String> severity = const Value.absent(),
                Value<String> message = const Value.absent(),
                Value<String?> projectId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedLogsCompanion(
                id: id,
                timestamp: timestamp,
                severity: severity,
                message: message,
                projectId: projectId,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                required DateTime timestamp,
                required String severity,
                required String message,
                Value<String?> projectId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedLogsCompanion.insert(
                id: id,
                timestamp: timestamp,
                severity: severity,
                message: message,
                projectId: projectId,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedLogsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedLogsTable,
      CachedLog,
      $$CachedLogsTableFilterComposer,
      $$CachedLogsTableOrderingComposer,
      $$CachedLogsTableAnnotationComposer,
      $$CachedLogsTableCreateCompanionBuilder,
      $$CachedLogsTableUpdateCompanionBuilder,
      (CachedLog, BaseReferences<_$AppDatabase, $CachedLogsTable, CachedLog>),
      CachedLog,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$CachedMetricsTableTableManager get cachedMetrics =>
      $$CachedMetricsTableTableManager(_db, _db.cachedMetrics);
  $$CachedLogsTableTableManager get cachedLogs =>
      $$CachedLogsTableTableManager(_db, _db.cachedLogs);
}

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(appDatabase)
final appDatabaseProvider = AppDatabaseProvider._();

final class AppDatabaseProvider
    extends $FunctionalProvider<AppDatabase, AppDatabase, AppDatabase>
    with $Provider<AppDatabase> {
  AppDatabaseProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'appDatabaseProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$appDatabaseHash();

  @$internal
  @override
  $ProviderElement<AppDatabase> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  AppDatabase create(Ref ref) {
    return appDatabase(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AppDatabase value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AppDatabase>(value),
    );
  }
}

String _$appDatabaseHash() => r'4db1c5efe1a73afafa926c6e91d12e49a68b1abc';
