import 'package:flutter/material.dart';
import '../../theme/app_theme.dart';

class SyntaxHighlightingController extends TextEditingController {
  SyntaxHighlightingController({super.text});

  @override
  TextSpan buildTextSpan({
    required BuildContext context,
    TextStyle? style,
    required bool withComposing,
  }) {
    var children = <TextSpan>[];
    final pattern = RegExp(
      r'(?:"[^"]*")|' // String literals
      r'(?:\b(?:AND|OR|NOT)\b)|' // Logical Operators
      r'(?:(?:severity|resource\.type|insertId|timestamp|logName|textPayload|protoPayload|jsonPayload)[\.]?[a-zA-Z0-9_]*)|' // Keywords
      r'(?:[<>=!]+)', // Comparison operators
    );

    var lastMatchEnd = 0;
    for (final match in pattern.allMatches(text)) {
      if (match.start > lastMatchEnd) {
        children.add(
          TextSpan(
            text: text.substring(lastMatchEnd, match.start),
            style: style,
          ),
        );
      }

      final matchedText = match.group(0)!;
      var highlightStyle = style;

      if (matchedText.startsWith('"')) {
        highlightStyle = style?.copyWith(
          color: AppColors.primaryCyan.withValues(alpha: 0.8),
        );
      } else if (['AND', 'OR', 'NOT'].contains(matchedText)) {
        highlightStyle = style?.copyWith(
          color: AppColors.secondaryPurple,
          fontWeight: FontWeight.bold,
        );
      } else if (RegExp(r'^[<>=!]+$').hasMatch(matchedText)) {
        highlightStyle = style?.copyWith(color: AppColors.warning);
      } else {
        // Must be a keyword
        highlightStyle = style?.copyWith(
          color: AppColors.primaryCyan,
          fontWeight: FontWeight.bold,
        );
      }

      children.add(TextSpan(text: matchedText, style: highlightStyle));

      lastMatchEnd = match.end;
    }

    if (lastMatchEnd < text.length) {
      children.add(TextSpan(text: text.substring(lastMatchEnd), style: style));
    }

    return TextSpan(style: style, children: children);
  }
}
