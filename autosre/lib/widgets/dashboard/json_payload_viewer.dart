import 'dart:convert';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';

class JsonPayloadViewer extends StatefulWidget {
  final Map<String, dynamic> json;
  final void Function(String path, String value) onValueTap;

  const JsonPayloadViewer({
    super.key,
    required this.json,
    required this.onValueTap,
  });

  @override
  State<JsonPayloadViewer> createState() => _JsonPayloadViewerState();
}

class _JsonPayloadViewerState extends State<JsonPayloadViewer> {
  final List<TapGestureRecognizer> _recognizers = [];

  @override
  void dispose() {
    for (final r in _recognizers) {
      r.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Clear old recognizers on rebuild
    for (final r in _recognizers) {
      r.dispose();
    }
    _recognizers.clear();

    return SelectableText.rich(
      TextSpan(
        style: GoogleFonts.jetBrainsMono(
          fontSize: 10,
          color: AppColors.textPrimary,
          height: 1.4,
        ),
        children: [
          const TextSpan(text: '{\n'),
          ..._buildNodes(widget.json, '', 1),
          const TextSpan(text: '}'),
        ],
      ),
    );
  }

  List<InlineSpan> _buildNodes(
    Map<String, dynamic> map,
    String pathPrefix,
    int indentLevel,
  ) {
    final spans = <InlineSpan>[];
    final indent = '  ' * indentLevel;

    final keys = map.keys.toList();
    for (var i = 0; i < keys.length; i++) {
      final key = keys[i];
      final value = map[key];
      final isLast = i == keys.length - 1;

      final currentPath = pathPrefix.isEmpty ? key : '$pathPrefix.$key';

      // Key
      spans.add(
        TextSpan(
          text: '$indent"$key"',
          style: TextStyle(color: AppColors.primaryCyan.withValues(alpha: 0.9)),
        ),
      );
      spans.add(const TextSpan(text: ': '));

      // Value
      if (value is Map<String, dynamic>) {
        spans.add(const TextSpan(text: '{\n'));
        spans.addAll(_buildNodes(value, currentPath, indentLevel + 1));
        spans.add(TextSpan(text: '$indent}${isLast ? "" : ","}\n'));
      } else if (value is List) {
        final strVal = jsonEncode(value);
        spans.add(
          TextSpan(
            text: '$strVal${isLast ? "" : ","}\n',
            style: const TextStyle(color: AppColors.textPrimary),
          ),
        );
      } else {
        // Primitive
        final isString = value is String;
        final displayVal = isString ? '"$value"' : value.toString();

        var color = AppColors.textPrimary;
        if (isString) {
          color = AppColors.primaryCyan;
        } else if (value is num) {
          color = AppColors.warning;
        } else if (value is bool) {
          color = AppColors.secondaryPurple;
        } else if (value == null) {
          color = AppColors.textMuted;
        }

        final recognizer = TapGestureRecognizer()
          ..onTap = () {
            widget.onValueTap(currentPath, displayVal);
          };
        _recognizers.add(recognizer);

        spans.add(
          TextSpan(
            text: displayVal,
            style: TextStyle(
              color: color,
              decoration: TextDecoration.underline,
              decorationColor: color.withValues(alpha: 0.4),
              decorationStyle: TextDecorationStyle.dotted,
            ),
            recognizer: recognizer,
          ),
        );

        spans.add(TextSpan(text: '${isLast ? "" : ","}\n'));
      }
    }

    return spans;
  }
}
