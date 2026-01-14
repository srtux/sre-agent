import 'package:flutter/material.dart';

class ErrorPlaceholder extends StatelessWidget {
  final Object error;

  const ErrorPlaceholder({super.key, required this.error});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(8.0),
      child: Text(
        "Error rendering widget: $error",
        style: const TextStyle(color: Colors.red),
      ),
    );
  }
}
