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

/// Maximum recursion depth to prevent stack overflow on deeply nested data.
const int _maxFlattenDepth = 50;

/// Recursively flattens a BigQuery value wrapper.
///
/// [depth] tracks recursion depth and bails out at [_maxFlattenDepth] to
/// prevent stack overflow in the browser on malformed or circular data.
dynamic flattenBigQueryValue(dynamic value, {int depth = 0}) {
  if (value == null) return null;
  if (depth > _maxFlattenDepth) return value;

  if (value is Map) {
    // Check for BigQuery's row/record field list: {"f": [...]}
    if (value.containsKey('f') && value['f'] is List) {
      final fields = value['f'] as List;
      // If it's a list of {v: ...}, it's a record/struct
      final flattened = fields
          .map((f) => flattenBigQueryValue(f, depth: depth + 1))
          .toList();

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
      return flattenBigQueryValue(v, depth: depth + 1);
    }

    // It's a normal map - recurse into its entries
    return value.map(
      (k, v) =>
          MapEntry(k.toString(), flattenBigQueryValue(v, depth: depth + 1)),
    );
  }

  if (value is List) {
    return value
        .map((item) => flattenBigQueryValue(item, depth: depth + 1))
        .toList();
  }

  // If it's a string that looks like JSON, try to parse it (common for BQ JSON type)
  if (value is String) {
    final trimmed = value.trim();
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
        (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        final decoded = json.decode(trimmed);
        return flattenBigQueryValue(decoded, depth: depth + 1);
      } catch (_) {
        // Not valid JSON, return as string
      }
    }
  }

  return value;
}
