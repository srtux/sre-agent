import 'dart:async';
import 'package:flutter/foundation.dart';

Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  // Enforce that RenderFlex overflows cause tests to fail.
  // By default, Flutter tests only print overflow warnings to console but still pass.
  FlutterError.onError = (FlutterErrorDetails details) {
    if (details.exceptionAsString().contains('A RenderFlex overflowed')) {
      // Dump the exception to the failure queue
      throw Exception(
        'RenderFlex overflow detected during a test.\n\n$details',
      );
    }
    FlutterError.dumpErrorToConsole(details);
  };

  await testMain();
}
