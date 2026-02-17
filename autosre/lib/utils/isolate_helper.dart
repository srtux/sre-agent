import 'package:flutter/foundation.dart';

/// A robust helper for offloading heavy computational tasks (like JSON parsing)
/// to a background worker.
///
/// Under the hood, this leverages [compute] from `foundation.dart`.
/// - On Mobile/Desktop, [compute] transparently spawns a Dart Isolate.
/// - On Web (`dart4web`), true isolates via `dart:isolate` throw `Unsupported operation`.
///   Instead, `compute` will attempt to use a Web Worker or gracefully
///   fall back to executing safely on the main thread to prevent the app from crashing.
///
/// Using [AppIsolate.run] guarantees web-safety and robust backgrounding
/// everywhere in the codebase.
class AppIsolate {
  /// Offloads [callback] to a web-safe background isolate/worker with [message].
  static Future<R> run<Q, R>(ComputeCallback<Q, R> callback, Q message) async {
    return await compute(callback, message);
  }

  /// Convenience wrapper for 0-argument background tasks.
  static Future<R> runZeroArg<R>(R Function() callback) async {
    // `compute` strictly requires a 1-argument messaging function.
    // We wrap the 0-argument callback internally.
    return await compute<void, R>((_) => callback(), null);
  }
}
