import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';

/// Compact per-panel query input bar for manual data exploration.
///
/// Provides a text field with monospace font, search icon, run/loading indicator,
/// and clear button. Submits on Enter key press or "Run Query" button tap.
///
/// Supports an optional [languageLabel] shown as a prefix badge, and a
/// [multiLine] mode for longer queries such as SQL.
class ManualQueryBar extends StatefulWidget {
  final String hintText;
  final ValueChanged<String> onSubmit;
  final bool isLoading;
  final VoidCallback? onClear;
  final String? initialValue;

  /// Optional label shown as a leading badge (e.g. "SQL", "PromQL").
  final String? languageLabel;

  /// Color used for the language badge.
  final Color languageLabelColor;

  /// When true, the query bar expands to support multi-line input (e.g. SQL).
  final bool multiLine;

  const ManualQueryBar({
    super.key,
    required this.hintText,
    required this.onSubmit,
    this.isLoading = false,
    this.onClear,
    this.initialValue,
    this.languageLabel,
    this.languageLabelColor = AppColors.primaryCyan,
    this.multiLine = false,
  });

  @override
  State<ManualQueryBar> createState() => _ManualQueryBarState();
}

class _ManualQueryBarState extends State<ManualQueryBar> {
  late final TextEditingController _controller;
  late final FocusNode _focusNode;
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialValue);
    _hasText = _controller.text.isNotEmpty;
    _focusNode = FocusNode();
    _focusNode.addListener(_onFocusChanged);
    _controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    _focusNode.removeListener(_onFocusChanged);
    _controller.removeListener(_onTextChanged);
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _onFocusChanged() {
    setState(() {});
  }

  void _onTextChanged() {
    final hasText = _controller.text.isNotEmpty;
    if (hasText != _hasText) {
      setState(() => _hasText = hasText);
    }
  }

  void _handleSubmit() {
    final text = _controller.text.trim();
    if (text.isNotEmpty && !widget.isLoading) {
      widget.onSubmit(text);
    }
  }

  void _handleClear() {
    _controller.clear();
    widget.onClear?.call();
    _focusNode.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.multiLine) {
      return _buildMultiLineBar();
    }
    return _buildSingleLineBar();
  }

  Widget _buildSingleLineBar() {
    final isFocused = _focusNode.hasFocus;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      height: 40,
      decoration: BoxDecoration(
        color: isFocused
            ? AppColors.backgroundDark
            : AppColors.backgroundCard.withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isFocused
              ? AppColors.primaryCyan.withValues(alpha: 0.6)
              : AppColors.surfaceBorder.withValues(alpha: 0.5),
          width: 1,
        ),
        boxShadow: [
          if (isFocused)
            BoxShadow(
              color: AppColors.primaryCyan.withValues(alpha: 0.15),
              blurRadius: 10,
              spreadRadius: 1,
            ),
        ],
      ),
      child: Row(
        children: [
          // Language badge or search icon
          if (widget.languageLabel != null)
            _buildLanguageBadge()
          else
            const Padding(
              padding: EdgeInsets.only(left: 10, right: 6),
              child: Icon(
                Icons.search_rounded,
                size: 16,
                color: AppColors.textMuted,
              ),
            ),
          // Text input
          Expanded(
            child: KeyboardListener(
              focusNode: FocusNode(),
              onKeyEvent: (event) {
                if (event is KeyDownEvent &&
                    event.logicalKey == LogicalKeyboardKey.enter) {
                  _handleSubmit();
                }
              },
              child: TextField(
                controller: _controller,
                focusNode: _focusNode,
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 12,
                  color: AppColors.textPrimary,
                ),
                decoration: InputDecoration(
                  hintText: widget.hintText,
                  hintStyle: GoogleFonts.jetBrainsMono(
                    fontSize: 12,
                    color: AppColors.textMuted.withValues(alpha: 0.6),
                  ),
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(
                    vertical: 10,
                  ),
                  isDense: true,
                ),
                onSubmitted: (_) => _handleSubmit(),
              ),
            ),
          ),
          // Clear button (visible when text is present)
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
                    borderRadius: BorderRadius.circular(6),
                  ),
                ),
                tooltip: 'Clear',
              ),
            ),
          // Run Query button or loading spinner
          Padding(
            padding: const EdgeInsets.only(right: 4),
            child: widget.isLoading
                ? const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 10),
                    child: SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: AppColors.primaryCyan,
                      ),
                    ),
                  )
                : TextButton(
                    onPressed: _hasText ? _handleSubmit : null,
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.primaryCyan,
                      disabledForegroundColor:
                          AppColors.textMuted.withValues(alpha: 0.4),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                      ),
                      minimumSize: const Size(0, 30),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(6),
                      ),
                      textStyle: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    child: const Text('Run Query'),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildMultiLineBar() {
    final isFocused = _focusNode.hasFocus;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      constraints: const BoxConstraints(minHeight: 80, maxHeight: 200),
      decoration: BoxDecoration(
        color: isFocused
            ? AppColors.backgroundDark
            : AppColors.backgroundCard.withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isFocused
              ? AppColors.primaryCyan.withValues(alpha: 0.6)
              : AppColors.surfaceBorder.withValues(alpha: 0.5),
          width: 1,
        ),
        boxShadow: [
          if (isFocused)
            BoxShadow(
              color: AppColors.primaryCyan.withValues(alpha: 0.15),
              blurRadius: 10,
              spreadRadius: 1,
            ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header row with language badge and actions
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 6, 4, 0),
            child: Row(
              children: [
                if (widget.languageLabel != null) _buildLanguageBadge(),
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
                          borderRadius: BorderRadius.circular(6),
                        ),
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
                            strokeWidth: 2,
                            color: AppColors.primaryCyan,
                          ),
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
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          minimumSize: const Size(0, 28),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(6),
                          ),
                          textStyle: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
              ],
            ),
          ),
          // Multi-line text field
          Flexible(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(10, 4, 10, 8),
              child: KeyboardListener(
                focusNode: FocusNode(),
                onKeyEvent: (event) {
                  // Ctrl+Enter or Cmd+Enter to submit in multi-line mode
                  if (event is KeyDownEvent &&
                      event.logicalKey == LogicalKeyboardKey.enter &&
                      (HardwareKeyboard.instance.isControlPressed ||
                          HardwareKeyboard.instance.isMetaPressed)) {
                    _handleSubmit();
                  }
                },
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  maxLines: null,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 12,
                    color: AppColors.textPrimary,
                    height: 1.5,
                  ),
                  decoration: InputDecoration(
                    hintText: widget.hintText,
                    hintStyle: GoogleFonts.jetBrainsMono(
                      fontSize: 12,
                      color: AppColors.textMuted.withValues(alpha: 0.6),
                      height: 1.5,
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
}
