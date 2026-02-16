import 'dart:convert';

/// Flattens BigQuery's nested `{f: [{v: ...}, ...]}` or `{v: ...}` structure
/// into a clean Map/List hierarchical structure for display.
List<Map<String, dynamic>> flattenBigQueryResults(
  List<Map<String, dynamic>> rows,
) {
  return rows.map((row) {
    return row.map((key, value) => MapEntry(key, flattenBigQueryValue(value)));
  }).toList();
}

/// Recursively flattens a BigQuery value wrapper.
dynamic flattenBigQueryValue(dynamic value) {
  if (value == null) return null;

  if (value is Map) {
    // Check for BigQuery's row/record field list: {"f": [...]}
    if (value.containsKey('f') && value['f'] is List) {
      final fields = value['f'] as List;
      // If it's a list of {v: ...}, it's a record/struct
      final flattened = fields.map((f) => flattenBigQueryValue(f)).toList();

      // If all elements are simple values, or if we want to try to keep it as a list,
      // return as is. BQ sometimes returns STRUCTs as lists in this format.
      return flattened;
    }

    // Check for BigQuery's value wrapper: {"v": ...}
    if (value.containsKey('v')) {
      final v = value['v'];

      // BQ returns NULL as {"v": null} or just null.
      if (v == null) return null;

      // Recursively flatten the inner value
      return flattenBigQueryValue(v);
    }

    // It's a normal map - recurse into its entries
    return value.map((k, v) => MapEntry(k.toString(), flattenBigQueryValue(v)));
  }

  if (value is List) {
    return value.map((item) => flattenBigQueryValue(item)).toList();
  }

  // If it's a string that looks like JSON, try to parse it (common for BQ JSON type)
  if (value is String) {
    final trimmed = value.trim();
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
        (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        final decoded = json.decode(trimmed);
        return flattenBigQueryValue(decoded);
      } catch (_) {
        // Not valid JSON, return as string
      }
    }
  }

  return value;
}
