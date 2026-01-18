import 'dart:async';
import 'package:flutter/material.dart';
import 'app.dart';

void main() {
  runZonedGuarded(() {
    runApp(const SreNexusApp());
  }, (error, stack) {
    debugPrint('🔥 CRITICAL ERROR IN MAIN: $error');
    debugPrint(stack.toString());
  });
}
