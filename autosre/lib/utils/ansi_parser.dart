import 'package:flutter/material.dart';

/// A utility to parse ANSI escape codes and convert them to Flutter TextSpans.
/// Supports basic colors (30-37, 90-97), bold (1), and reset (0).
class AnsiParser {
  static final RegExp _ansiRegex = RegExp(r'\x1B\[[0-9;]*m');

  /// Parses a string containing ANSI escape codes into a [TextSpan].
  static TextSpan parse(String text, {TextStyle? baseStyle}) {
    if (!text.contains('\x1B')) {
      return TextSpan(text: text, style: baseStyle);
    }

    final spans = <TextSpan>[];
    var lastMatchEnd = 0;
    var currentStyle = baseStyle ?? const TextStyle();

    final matches = _ansiRegex.allMatches(text);
    for (final match in matches) {
      if (match.start > lastMatchEnd) {
        spans.add(
          TextSpan(
            text: text.substring(lastMatchEnd, match.start),
            style: currentStyle,
          ),
        );
      }

      final code = text.substring(match.start, match.end);
      currentStyle = _updateStyle(currentStyle, code, baseStyle);
      lastMatchEnd = match.end;
    }

    if (lastMatchEnd < text.length) {
      spans.add(
        TextSpan(text: text.substring(lastMatchEnd), style: currentStyle),
      );
    }

    return TextSpan(children: spans);
  }

  static TextStyle _updateStyle(
    TextStyle current,
    String ansiCode,
    TextStyle? baseStyle,
  ) {
    // strip \x1B[ and m
    final cleanCode = ansiCode.substring(2, ansiCode.length - 1);
    if (cleanCode.isEmpty) return baseStyle ?? const TextStyle();

    final codes = cleanCode
        .split(';')
        .map((e) => int.tryParse(e))
        .whereType<int>()
        .toList();

    if (codes.isEmpty) return current;

    var newStyle = current;
    for (final code in codes) {
      if (code == 0) {
        newStyle = baseStyle ?? const TextStyle();
      } else if (code == 1) {
        newStyle = newStyle.copyWith(fontWeight: FontWeight.bold);
      } else if (code == 2) {
        newStyle = newStyle.copyWith(
          color: current.color?.withValues(alpha: 0.5),
        );
      } else if (code == 3) {
        newStyle = newStyle.copyWith(fontStyle: FontStyle.italic);
      } else if (code == 4) {
        newStyle = newStyle.copyWith(decoration: TextDecoration.underline);
      } else if (code >= 30 && code <= 37) {
        newStyle = newStyle.copyWith(
          color: _getColor(code - 30, bright: false),
        );
      } else if (code >= 40 && code <= 47) {
        // Background colors - maybe implementation later if needed
      } else if (code >= 90 && code <= 97) {
        newStyle = newStyle.copyWith(color: _getColor(code - 90, bright: true));
      }
    }
    return newStyle;
  }

  static Color _getColor(int index, {required bool bright}) =>
      // Custom premium palette for dark theme
      switch (index) {
        0 => bright ? Colors.grey[400]! : Colors.grey[800]!, // Black/Grey
        1 => bright ? const Color(0xFFFF5252) : const Color(0xFFE57373), // Red
        2 => bright ? const Color(0xFF69F0AE) : const Color(0xFF81C784), // Green
        3 => bright ? const Color(0xFFFFD740) : const Color(0xFFFFF176), // Yellow
        4 => bright ? const Color(0xFF448AFF) : const Color(0xFF64B5F6), // Blue
        5 => bright ? const Color(0xFFE040FB) : const Color(0xFFF06292), // Magenta
        6 => bright ? const Color(0xFF18FFFF) : const Color(0xFF4DD0E1), // Cyan
        7 => bright ? Colors.white : Colors.grey[300]!, // White
        _ => Colors.white,
      };
}
