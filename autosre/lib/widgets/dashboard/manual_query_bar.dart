import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';
import 'query_autocomplete_overlay.dart';
import 'query_helpers.dart';

/// Compact per-panel query input bar for manual data exploration.
///
/// Features:
/// - Monospace text field with optional language badge
/// - **Autocomplete**: Context-aware keyword suggestions while typing
/// - **Helper templates**: Lightbulb button opens a pre-built query picker
/// - **Natural language toggle**: Switch between structured query and NL mode
/// - Multi-line mode for SQL-style queries (Ctrl+Enter to submit)
class ManualQueryBar extends StatefulWidget {
  final String hintText;
  final ValueChanged<String> onSubmit;
  final bool isLoading;
  final VoidCallback? onClear;
  final String? initialValue;
  final TextEditingController? controller;

  /// Optional label shown as a leading badge (e.g. "SQL", "PromQL").
  final String? languageLabel;

  /// Color used for the language badge.
  final Color languageLabelColor;

  /// When true, the query bar expands to support multi-line input (e.g. SQL).
  final bool multiLine;

  /// Autocomplete snippets shown while typing.
  final List<QuerySnippet> snippets;

  /// Pre-built query templates shown in the helper popup.
  final List<QueryTemplate> templates;

  /// Whether to show the natural language mode toggle.
  final bool enableNaturalLanguage;

  /// Hint text shown when in natural language mode.
  final String naturalLanguageHint;

  /// Example NL prompts shown in the helper popup.
  final List<String> naturalLanguageExamples;

  /// Called with `(query, isNaturalLanguage)` when submitted.
  /// Use this instead of [onSubmit] when NL mode matters.
  final void Function(String query, bool isNaturalLanguage)?
      onSubmitWithMode;

  const ManualQueryBar({
    super.key,
    required this.hintText,
    required this.onSubmit,
    this.isLoading = false,
    this.onClear,
    this.initialValue,
    this.controller,
    this.languageLabel,
    this.languageLabelColor = AppColors.primaryCyan,
    this.multiLine = false,
    this.snippets = const [],
    this.templates = const [],
    this.enableNaturalLanguage = false,
    this.naturalLanguageHint = 'Describe what you want to find...',
    this.naturalLanguageExamples = const [],
    this.onSubmitWithMode,
  });

  @override
  State<ManualQueryBar> createState() => _ManualQueryBarState();
}

class _ManualQueryBarState extends State<ManualQueryBar> {
  late final TextEditingController _controller;
  late final FocusNode _focusNode;
  bool _hasText = false;
  bool _ownsController = false;

  /// Whether autocomplete overlay is visible.
  bool _showAutocomplete = false;

  /// Filtered autocomplete suggestions.
  List<QuerySnippet> _filteredSnippets = [];

  /// Index of the currently keyboard-highlighted suggestion.
  int _highlightedIndex = -1;

  /// Whether natural language mode is active.
  bool _isNaturalLanguage = false;

  /// LayerLink for positioning the autocomplete overlay.
  final LayerLink _layerLink = LayerLink();

  /// OverlayEntry for the autocomplete dropdown.
  OverlayEntry? _overlayEntry;

  /// OverlayEntry for the templates popup.
  OverlayEntry? _templatesOverlay;

  @override
  void initState() {
    super.initState();
    if (widget.controller != null) {
      _controller = widget.controller!;
      if (widget.initialValue != null && _controller.text.isEmpty) {
        _controller.text = widget.initialValue!;
      }
    } else {
      _controller = TextEditingController(text: widget.initialValue);
      _ownsController = true;
    }
    _hasText = _controller.text.isNotEmpty;
    _focusNode = FocusNode();
    _focusNode.addListener(_onFocusChanged);
    _controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    _removeOverlay();
    _removeTemplatesOverlay();
    _focusNode.removeListener(_onFocusChanged);
    _controller.removeListener(_onTextChanged);
    if (_ownsController) {
      _controller.dispose();
    }
    _focusNode.dispose();
    super.dispose();
  }

  void _onFocusChanged() {
    setState(() {});
    if (!_focusNode.hasFocus) {
      // Delay removal so tap on overlay can register first
      Future.delayed(const Duration(milliseconds: 200), () {
        if (!_focusNode.hasFocus) _removeOverlay();
      });
    }
  }

  void _onTextChanged() {
    final hasText = _controller.text.isNotEmpty;
    if (hasText != _hasText) {
      setState(() => _hasText = hasText);
    }
    // Update autocomplete
    if (!_isNaturalLanguage && widget.snippets.isNotEmpty) {
      _updateAutocomplete();
    }
  }

  void _updateAutocomplete() {
    final text = _controller.text;
    if (text.isEmpty) {
      _removeOverlay();
      return;
    }

    // Get the current word being typed (after the last space)
    final cursorPos = _controller.selection.baseOffset;
    final beforeCursor =
        cursorPos >= 0 && cursorPos <= text.length
            ? text.substring(0, cursorPos)
            : text;
    final lastSpace = beforeCursor.lastIndexOf(' ');
    final currentWord =
        lastSpace >= 0 ? beforeCursor.substring(lastSpace + 1) : beforeCursor;

    if (currentWord.isEmpty) {
      _removeOverlay();
      return;
    }

    final query = currentWord.toLowerCase();
    _filteredSnippets = widget.snippets.where((s) {
      final label = s.label.toLowerCase();
      if (label.contains(query)) return true;

      // Special handling for key="value" style autocompletes (MQL/Logs)
      const prefixes = ['metric.type="', 'resource.type="', 'metric.labels.', 'resource.labels.'];
      for (final p in prefixes) {
        if (query.startsWith(p) && label.startsWith(p)) {
          final queryVal = query.substring(p.length);
          final labelVal = label.substring(p.length);
          return labelVal.contains(queryVal);
        }
      }
      return false;
    }).take(8).toList();

    if (_filteredSnippets.isEmpty) {
      _removeOverlay();
      return;
    }

    _highlightedIndex = -1;
    _showOverlay();
  }

  void _showOverlay() {
    _removeOverlay();
    _showAutocomplete = true;
    _overlayEntry = OverlayEntry(
      builder: (context) => Positioned(
        width: 400,
        child: CompositedTransformFollower(
          link: _layerLink,
          showWhenUnlinked: false,
          offset: const Offset(0, 44),
          child: QueryAutocompleteOverlay(
            suggestions: _filteredSnippets,
            highlightedIndex: _highlightedIndex,
            onSelect: _insertSnippet,
          ),
        ),
      ),
    );
    Overlay.of(context).insert(_overlayEntry!);
  }

  void _removeOverlay() {
    _overlayEntry?.remove();
    _overlayEntry = null;
    _showAutocomplete = false;
  }

  void _insertSnippet(QuerySnippet snippet) {
    final text = _controller.text;
    final cursorPos = _controller.selection.baseOffset;
    final beforeCursor =
        cursorPos >= 0 && cursorPos <= text.length
            ? text.substring(0, cursorPos)
            : text;
    final afterCursor =
        cursorPos >= 0 && cursorPos <= text.length
            ? text.substring(cursorPos)
            : '';

    // Replace the current partial word
    final lastSpace = beforeCursor.lastIndexOf(' ');
    final prefix =
        lastSpace >= 0 ? beforeCursor.substring(0, lastSpace + 1) : '';

    final newText = '$prefix${snippet.insertText}$afterCursor';
    _controller.text = newText;
    _controller.selection = TextSelection.collapsed(
      offset: prefix.length + snippet.insertText.length,
    );
    _removeOverlay();
    _focusNode.requestFocus();
  }

  void _handleSubmit() {
    final text = _controller.text.trim();
    if (text.isNotEmpty && !widget.isLoading) {
      _removeOverlay();
      if (widget.onSubmitWithMode != null) {
        widget.onSubmitWithMode!(text, _isNaturalLanguage);
      } else {
        widget.onSubmit(text);
      }
    }
  }

  void _handleClear() {
    _controller.clear();
    _removeOverlay();
    widget.onClear?.call();
    _focusNode.requestFocus();
  }

  void _toggleNaturalLanguage() {
    setState(() => _isNaturalLanguage = !_isNaturalLanguage);
    _removeOverlay();
    _focusNode.requestFocus();
  }

  void _showTemplatesPopup() {
    if (widget.templates.isEmpty && widget.naturalLanguageExamples.isEmpty) {
      return;
    }
    _removeTemplatesOverlay();
    _templatesOverlay = OverlayEntry(
      builder: (context) => GestureDetector(
        behavior: HitTestBehavior.translucent,
        onTap: _removeTemplatesOverlay,
        child: Stack(
          children: [
            CompositedTransformFollower(
              link: _layerLink,
              showWhenUnlinked: false,
              offset: const Offset(0, 44),
              child: QueryTemplatesPicker(
                templates: widget.templates,
                naturalLanguageExamples: widget.naturalLanguageExamples,
                onNaturalLanguageSelect: (example) {
                  _removeTemplatesOverlay();
                  setState(() => _isNaturalLanguage = true);
                  _controller.text = example;
                  _focusNode.requestFocus();
                },
                onSelect: (template) {
                  _removeTemplatesOverlay();
                  setState(() => _isNaturalLanguage = false);
                  _controller.text = template.query;
                  _controller.selection = TextSelection.collapsed(
                    offset: template.query.length,
                  );
                  _focusNode.requestFocus();
                },
              ),
            ),
          ],
        ),
      ),
    );
    Overlay.of(context).insert(_templatesOverlay!);
  }

  void _removeTemplatesOverlay() {
    _templatesOverlay?.remove();
    _templatesOverlay = null;
  }

  KeyEventResult _handleKeyEvent(KeyEvent event) {
    if (event is! KeyDownEvent) return KeyEventResult.ignored;

    if (_showAutocomplete && _filteredSnippets.isNotEmpty) {
      if (event.logicalKey == LogicalKeyboardKey.arrowDown) {
        setState(() {
          _highlightedIndex =
              (_highlightedIndex + 1) % _filteredSnippets.length;
        });
        _showOverlay(); // Rebuild overlay
        return KeyEventResult.handled;
      }
      if (event.logicalKey == LogicalKeyboardKey.arrowUp) {
        setState(() {
          _highlightedIndex = _highlightedIndex <= 0
              ? _filteredSnippets.length - 1
              : _highlightedIndex - 1;
        });
        _showOverlay();
        return KeyEventResult.handled;
      }
      if (event.logicalKey == LogicalKeyboardKey.tab ||
          (event.logicalKey == LogicalKeyboardKey.enter &&
              _highlightedIndex >= 0)) {
        if (_highlightedIndex >= 0 &&
            _highlightedIndex < _filteredSnippets.length) {
          _insertSnippet(_filteredSnippets[_highlightedIndex]);
          return KeyEventResult.handled;
        }
      }
      if (event.logicalKey == LogicalKeyboardKey.escape) {
        _removeOverlay();
        return KeyEventResult.handled;
      }
    }

    // Submit handling
    if (!widget.multiLine &&
        event.logicalKey == LogicalKeyboardKey.enter &&
        _highlightedIndex < 0) {
      _handleSubmit();
      return KeyEventResult.handled;
    }
    if (widget.multiLine &&
        event.logicalKey == LogicalKeyboardKey.enter &&
        (HardwareKeyboard.instance.isControlPressed ||
            HardwareKeyboard.instance.isMetaPressed)) {
      _handleSubmit();
      return KeyEventResult.handled;
    }

    return KeyEventResult.ignored;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.multiLine) return _buildMultiLineBar();
    return _buildSingleLineBar();
  }

  // ===========================================================================
  // Single-line bar
  // ===========================================================================

  Widget _buildSingleLineBar() {
    final isFocused = _focusNode.hasFocus;
    final effectiveHint =
        _isNaturalLanguage ? widget.naturalLanguageHint : widget.hintText;

    return CompositedTransformTarget(
      link: _layerLink,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        height: 40,
        decoration: BoxDecoration(
          color: isFocused
              ? AppColors.backgroundDark
              : AppColors.backgroundCard.withValues(alpha: 0.8),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: _isNaturalLanguage
                ? AppColors.secondaryPurple.withValues(alpha: 0.6)
                : isFocused
                    ? AppColors.primaryCyan.withValues(alpha: 0.6)
                    : AppColors.surfaceBorder.withValues(alpha: 0.5),
            width: 1,
          ),
          boxShadow: [
            if (isFocused)
              BoxShadow(
                color: (_isNaturalLanguage
                        ? AppColors.secondaryPurple
                        : AppColors.primaryCyan)
                    .withValues(alpha: 0.15),
                blurRadius: 10,
                spreadRadius: 1,
              ),
          ],
        ),
        child: Row(
          children: [
            // NL toggle or language badge or search icon
            if (widget.enableNaturalLanguage)
              _buildNlToggle()
            else if (widget.languageLabel != null)
              _buildLanguageBadge()
            else
              const Padding(
                padding: EdgeInsets.only(left: 10, right: 6),
                child: Icon(Icons.search_rounded,
                    size: 16, color: AppColors.textMuted),
              ),
            // Text input
            Expanded(
              child: Focus(
                onKeyEvent: (_, event) => _handleKeyEvent(event),
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  style: _isNaturalLanguage
                      ? GoogleFonts.inter(
                          fontSize: 12,
                          color: AppColors.textPrimary,
                        )
                      : GoogleFonts.jetBrainsMono(
                          fontSize: 12,
                          color: AppColors.textPrimary,
                        ),
                  decoration: InputDecoration(
                    hintText: effectiveHint,
                    hintStyle: (_isNaturalLanguage
                            ? GoogleFonts.inter(fontSize: 12)
                            : GoogleFonts.jetBrainsMono(fontSize: 12))
                        .copyWith(
                      color: AppColors.textMuted.withValues(alpha: 0.6),
                    ),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(vertical: 10),
                    isDense: true,
                  ),
                  onSubmitted: (_) => _handleSubmit(),
                ),
              ),
            ),
            // Helper templates button
            if (widget.templates.isNotEmpty ||
                widget.naturalLanguageExamples.isNotEmpty)
              _buildHelperButton(),
            // Clear button
            if (_hasText && !widget.isLoading)
              SizedBox(
                width: 28,
                height: 28,
                child: IconButton(
                  icon: const Icon(Icons.close_rounded, size: 14),
                  color: AppColors.textMuted,
                  onPressed: _handleClear,
                  padding: EdgeInsets.zero,
                  style: IconButton.styleFrom(
                    minimumSize: const Size(28, 28),
                    backgroundColor: Colors.transparent,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(6)),
                  ),
                  tooltip: 'Clear',
                ),
              ),
            // Run Query / loading
            Padding(
              padding: const EdgeInsets.only(right: 4),
              child: widget.isLoading
                  ? const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 10),
                      child: SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: AppColors.primaryCyan),
                      ),
                    )
                  : TextButton(
                      onPressed: _hasText ? _handleSubmit : null,
                      style: TextButton.styleFrom(
                        foregroundColor: AppColors.primaryCyan,
                        disabledForegroundColor:
                            AppColors.textMuted.withValues(alpha: 0.4),
                        padding: const EdgeInsets.symmetric(horizontal: 10),
                        minimumSize: const Size(0, 30),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(6)),
                        textStyle: const TextStyle(
                            fontSize: 11, fontWeight: FontWeight.w600),
                      ),
                      child: const Text('Run Query'),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // Multi-line bar
  // ===========================================================================

  Widget _buildMultiLineBar() {
    final isFocused = _focusNode.hasFocus;
    final effectiveHint =
        _isNaturalLanguage ? widget.naturalLanguageHint : widget.hintText;

    return CompositedTransformTarget(
      link: _layerLink,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        constraints: const BoxConstraints(minHeight: 80, maxHeight: 200),
        decoration: BoxDecoration(
          color: isFocused
              ? AppColors.backgroundDark
              : AppColors.backgroundCard.withValues(alpha: 0.8),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _isNaturalLanguage
                ? AppColors.secondaryPurple.withValues(alpha: 0.6)
                : isFocused
                    ? AppColors.primaryCyan.withValues(alpha: 0.6)
                    : AppColors.surfaceBorder.withValues(alpha: 0.5),
            width: 1,
          ),
          boxShadow: [
            if (isFocused)
              BoxShadow(
                color: (_isNaturalLanguage
                        ? AppColors.secondaryPurple
                        : AppColors.primaryCyan)
                    .withValues(alpha: 0.15),
                blurRadius: 10,
                spreadRadius: 1,
              ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header row
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 6, 4, 0),
              child: Row(
                children: [
                  if (widget.enableNaturalLanguage) _buildNlToggle(),
                  if (widget.languageLabel != null && !_isNaturalLanguage)
                    _buildLanguageBadge(),
                  if (widget.templates.isNotEmpty ||
                      widget.naturalLanguageExamples.isNotEmpty)
                    _buildHelperButton(),
                  const Spacer(),
                  if (_hasText && !widget.isLoading)
                    SizedBox(
                      width: 28,
                      height: 28,
                      child: IconButton(
                        icon: const Icon(Icons.close_rounded, size: 14),
                        color: AppColors.textMuted,
                        onPressed: _handleClear,
                        padding: EdgeInsets.zero,
                        style: IconButton.styleFrom(
                          minimumSize: const Size(28, 28),
                          backgroundColor: Colors.transparent,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(6)),
                        ),
                        tooltip: 'Clear',
                      ),
                    ),
                  widget.isLoading
                      ? const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 10),
                          child: SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: AppColors.primaryCyan),
                          ),
                        )
                      : TextButton.icon(
                          onPressed: _hasText ? _handleSubmit : null,
                          icon: const Icon(Icons.play_arrow_rounded, size: 16),
                          label: const Text('Run'),
                          style: TextButton.styleFrom(
                            foregroundColor: AppColors.primaryCyan,
                            disabledForegroundColor:
                                AppColors.textMuted.withValues(alpha: 0.4),
                            padding:
                                const EdgeInsets.symmetric(horizontal: 10),
                            minimumSize: const Size(0, 28),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(6)),
                            textStyle: const TextStyle(
                                fontSize: 11, fontWeight: FontWeight.w600),
                          ),
                        ),
                ],
              ),
            ),
            // Text field
            Flexible(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(10, 4, 10, 8),
                child: Focus(
                  onKeyEvent: (_, event) => _handleKeyEvent(event),
                  child: TextField(
                    controller: _controller,
                    focusNode: _focusNode,
                    maxLines: null,
                    style: _isNaturalLanguage
                        ? GoogleFonts.inter(
                            fontSize: 12,
                            color: AppColors.textPrimary,
                            height: 1.5,
                          )
                        : GoogleFonts.jetBrainsMono(
                            fontSize: 12,
                            color: AppColors.textPrimary,
                            height: 1.5,
                          ),
                    decoration: InputDecoration(
                      hintText: effectiveHint,
                      hintStyle: (_isNaturalLanguage
                              ? GoogleFonts.inter(fontSize: 12, height: 1.5)
                              : GoogleFonts.jetBrainsMono(
                                  fontSize: 12, height: 1.5))
                          .copyWith(
                        color: AppColors.textMuted.withValues(alpha: 0.6),
                      ),
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      contentPadding: EdgeInsets.zero,
                      isDense: true,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // Shared sub-widgets
  // ===========================================================================

  Widget _buildNlToggle() {
    return Tooltip(
      message: _isNaturalLanguage
          ? 'Switch to structured query'
          : 'Switch to natural language',
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: _toggleNaturalLanguage,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          margin: const EdgeInsets.only(left: 6, right: 6),
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: _isNaturalLanguage
                ? AppColors.secondaryPurple.withValues(alpha: 0.15)
                : widget.languageLabelColor.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: _isNaturalLanguage
                  ? AppColors.secondaryPurple.withValues(alpha: 0.3)
                  : widget.languageLabelColor.withValues(alpha: 0.25),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _isNaturalLanguage
                    ? Icons.auto_awesome_rounded
                    : Icons.code_rounded,
                size: 11,
                color: _isNaturalLanguage
                    ? AppColors.secondaryPurple
                    : widget.languageLabelColor,
              ),
              const SizedBox(width: 4),
              Text(
                _isNaturalLanguage
                    ? 'NL'
                    : (widget.languageLabel ?? 'Query'),
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 9,
                  fontWeight: FontWeight.w600,
                  color: _isNaturalLanguage
                      ? AppColors.secondaryPurple
                      : widget.languageLabelColor,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLanguageBadge() {
    return Container(
      margin: const EdgeInsets.only(left: 8, right: 8),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: widget.languageLabelColor.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: widget.languageLabelColor.withValues(alpha: 0.25),
        ),
      ),
      child: Text(
        widget.languageLabel!,
        style: GoogleFonts.jetBrainsMono(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          color: widget.languageLabelColor,
        ),
      ),
    );
  }

  Widget _buildHelperButton() {
    return Tooltip(
      message: 'Query helpers & templates',
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: _showTemplatesPopup,
        child: Container(
          width: 28,
          height: 28,
          alignment: Alignment.center,
          child: Icon(
            Icons.lightbulb_outline_rounded,
            size: 15,
            color: AppColors.warning.withValues(alpha: 0.8),
          ),
        ),
      ),
    );
  }
}
