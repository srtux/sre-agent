import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';
import 'query_helpers.dart';

/// Dropdown overlay showing autocomplete suggestions for query input.
///
/// Appears below the query bar when typing, filtered by the current
/// input text. Supports keyboard navigation (arrow keys + Enter).
class QueryAutocompleteOverlay extends StatelessWidget {
  /// Filtered suggestions to display.
  final List<QuerySnippet> suggestions;

  /// Index of the currently highlighted suggestion (-1 = none).
  final int highlightedIndex;

  /// Called when the user picks a suggestion.
  final ValueChanged<QuerySnippet> onSelect;

  const QueryAutocompleteOverlay({
    super.key,
    required this.suggestions,
    required this.onSelect,
    this.highlightedIndex = -1,
  });

  @override
  Widget build(BuildContext context) {
    if (suggestions.isEmpty) return const SizedBox.shrink();

    return Container(
      constraints: const BoxConstraints(maxHeight: 240),
      decoration: BoxDecoration(
        color: const Color(0xFF1A2332),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: AppColors.surfaceBorder.withValues(alpha: 0.5),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.4),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(10),
        child: ListView.builder(
          padding: const EdgeInsets.symmetric(vertical: 4),
          shrinkWrap: true,
          itemCount: suggestions.length,
          itemBuilder: (context, index) {
            final s = suggestions[index];
            final isHighlighted = index == highlightedIndex;
            return InkWell(
              onTap: () => onSelect(s),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                color: isHighlighted
                    ? AppColors.primaryCyan.withValues(alpha: 0.12)
                    : Colors.transparent,
                child: Row(
                  children: [
                    // Category icon
                    Container(
                      width: 22,
                      height: 22,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: s.color.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(5),
                      ),
                      child: Icon(s.icon, size: 12, color: s.color),
                    ),
                    const SizedBox(width: 8),
                    // Label
                    Text(
                      s.label,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: isHighlighted
                            ? AppColors.primaryCyan
                            : AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Description
                    Expanded(
                      child: Text(
                        s.description,
                        style: TextStyle(
                          fontSize: 10,
                          color: AppColors.textMuted.withValues(alpha: 0.7),
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    // Category badge
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.05),
                        borderRadius: BorderRadius.circular(3),
                      ),
                      child: Text(
                        s.category,
                        style: TextStyle(
                          fontSize: 8,
                          color: AppColors.textMuted.withValues(alpha: 0.6),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

/// Popup panel showing pre-built query templates grouped by category.
///
/// Launched from the lightbulb helper button in the query bar.
class QueryTemplatesPicker extends StatelessWidget {
  final List<QueryTemplate> templates;
  final ValueChanged<QueryTemplate> onSelect;

  /// Optional list of natural language example prompts shown at the top.
  final List<String> naturalLanguageExamples;

  /// Called when a natural language example is tapped.
  final ValueChanged<String>? onNaturalLanguageSelect;

  const QueryTemplatesPicker({
    super.key,
    required this.templates,
    required this.onSelect,
    this.naturalLanguageExamples = const [],
    this.onNaturalLanguageSelect,
  });

  @override
  Widget build(BuildContext context) {
    // Group templates by category
    final grouped = <String, List<QueryTemplate>>{};
    for (final t in templates) {
      grouped.putIfAbsent(t.category, () => []).add(t);
    }

    return Container(
      constraints: const BoxConstraints(maxHeight: 420, maxWidth: 440),
      decoration: BoxDecoration(
        color: const Color(0xFF1A2332),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: AppColors.surfaceBorder.withValues(alpha: 0.5),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.5),
            blurRadius: 20,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: ListView(
          padding: const EdgeInsets.all(8),
          shrinkWrap: true,
          children: [
            // Natural language examples section
            if (naturalLanguageExamples.isNotEmpty &&
                onNaturalLanguageSelect != null) ...[
              _buildSectionHeader(
                'Ask in Plain English',
                Icons.chat_bubble_outline_rounded,
                AppColors.secondaryPurple,
              ),
              ...naturalLanguageExamples.map(
                (example) => _buildNlExampleItem(example),
              ),
              Divider(
                color: AppColors.surfaceBorder.withValues(alpha: 0.3),
                height: 16,
              ),
            ],
            // Template categories
            ...grouped.entries.expand((entry) => [
                  _buildSectionHeader(
                    entry.key,
                    entry.value.first.icon,
                    AppColors.primaryCyan,
                  ),
                  ...entry.value.map(_buildTemplateItem),
                  const SizedBox(height: 4),
                ]),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title, IconData icon, Color color) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(6, 4, 6, 4),
      child: Row(
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 6),
          Text(
            title,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: color,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTemplateItem(QueryTemplate t) {
    return InkWell(
      onTap: () => onSelect(t),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(t.icon, size: 14, color: AppColors.primaryCyan),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    t.title,
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    t.description,
                    style: TextStyle(
                      fontSize: 9,
                      color: AppColors.textMuted.withValues(alpha: 0.7),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 6),
            Icon(
              Icons.arrow_forward_ios_rounded,
              size: 10,
              color: AppColors.textMuted.withValues(alpha: 0.4),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNlExampleItem(String example) {
    return InkWell(
      onTap: () => onNaturalLanguageSelect?.call(example),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        child: Row(
          children: [
            Icon(
              Icons.auto_awesome_rounded,
              size: 12,
              color: AppColors.secondaryPurple.withValues(alpha: 0.8),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '"$example"',
                style: TextStyle(
                  fontSize: 11,
                  fontStyle: FontStyle.italic,
                  color: AppColors.textSecondary.withValues(alpha: 0.9),
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
