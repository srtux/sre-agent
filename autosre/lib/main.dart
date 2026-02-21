import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';

void main() {
  runZonedGuarded(
    () {
      runApp(const ProviderScope(child: SreNexusApp()));
    },
    (error, stack) {
      debugPrint('🔥 CRITICAL ERROR IN MAIN: $error');
      debugPrint(stack.toString());
    },
  );
}
