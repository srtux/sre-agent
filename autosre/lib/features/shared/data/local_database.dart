import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'local_database.g.dart';

class CachedMetrics extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get metricName => text()();
  DateTimeColumn get timestamp => dateTime()();
  RealColumn get value => real()();
  TextColumn get projectId => text().nullable()();
}

class CachedLogs extends Table {
  TextColumn get id => text()(); // Log entry unique ID
  DateTimeColumn get timestamp => dateTime()();
  TextColumn get severity => text()();
  TextColumn get message => text()();
  TextColumn get projectId => text().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}

@DriftDatabase(tables: [CachedMetrics, CachedLogs])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 1;

  static QueryExecutor _openConnection() {
    return driftDatabase(name: 'autosre_cache');
  }
}

@riverpod
AppDatabase appDatabase(Ref ref) {
  final db = AppDatabase();
  ref.onDispose(db.close);
  return db;
}
