import 'package:flutter/material.dart';
import '../../theme/app_theme.dart';

class BigQuerySqlSyntaxController extends TextEditingController {
  BigQuerySqlSyntaxController({super.text});

  @override
  TextSpan buildTextSpan({
    required BuildContext context,
    TextStyle? style,
    required bool withComposing,
  }) {
    var children = <TextSpan>[];

    // Pattern to match string literals, backticks, SQL keywords, and operators
    final pattern = RegExp(
      r'(?:"[^"]*")|' // String literals (double quotes)
      r"(?:'[^']*')|" // String literals (single quotes)
      r'(?:`[^`]*`)|' // Backtick identifiers
      // BigQuery SQL Keywords
      r'(?:\b(?:SELECT|FROM|WHERE|AND|OR|NOT|AS|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|USING|GROUP|BY|ORDER|DESC|ASC|LIMIT|OFFSET|HAVING|WITH|IN|IS|NULL|UNION|ALL|EXCEPT|INTERSECT|TRUE|FALSE|CAST|EXTRACT|BETWEEN|CASE|WHEN|THEN|ELSE|END|LIKE)\b)|'
      // Built-in SQL functions
      r'(?:\b(?:COUNT|SUM|AVG|MIN|MAX|ARRAY_AGG|STRING_AGG|COALESCE|IFNULL|TIMESTAMP|DATE|DATETIME|JSON_EXTRACT_SCALAR|REGEXP_CONTAINS)\b)|'
      r'(?:[<>=!]+)', // Comparison operators
      caseSensitive: false,
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

      if (matchedText.startsWith('"') || matchedText.startsWith("'")) {
        highlightStyle = style?.copyWith(
          color: AppColors.success, // Green for strings
        );
      } else if (matchedText.startsWith('`')) {
        highlightStyle = style?.copyWith(
          color: AppColors.primaryTeal, // Teal for backticked names
        );
      } else if (['AND', 'OR', 'NOT'].contains(matchedText.toUpperCase())) {
        highlightStyle = style?.copyWith(
          color: AppColors.secondaryPurple,
          fontWeight: FontWeight.bold,
        );
      } else if ([
        'SELECT',
        'FROM',
        'WHERE',
        'JOIN',
        'ON',
        'GROUP BY',
        'ORDER BY',
        'LIMIT',
      ].contains(matchedText.toUpperCase())) {
        highlightStyle = style?.copyWith(
          color: AppColors.primaryCyan, // Soft blue for structural keywords
          fontWeight: FontWeight.bold,
        );
      } else if (RegExp(r'^[<>=!]+$').hasMatch(matchedText)) {
        highlightStyle = style?.copyWith(color: AppColors.warning);
      } else if (RegExp(
        r'^[A-Z]+$',
        caseSensitive: false,
      ).hasMatch(matchedText)) {
        highlightStyle = style?.copyWith(
          color: AppColors.primaryCyan, // Fallback for other keywords/functions
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
