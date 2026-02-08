import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';

/// Compact per-panel query input bar for manual data exploration.
///
/// Provides a text field with monospace font, search icon, run/loading indicator,
/// and clear button. Submits on Enter key press or "Run Query" button tap.
class ManualQueryBar extends StatefulWidget {
  final String hintText;
  final ValueChanged<String> onSubmit;
  final bool isLoading;
  final VoidCallback? onClear;
  final String? initialValue;

  const ManualQueryBar({
    super.key,
    required this.hintText,
    required this.onSubmit,
    this.isLoading = false,
    this.onClear,
    this.initialValue,
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
    _controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    _controller.removeListener(_onTextChanged);
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
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
    return Container(
      height: 40,
      decoration: BoxDecoration(
        color: AppColors.backgroundCard.withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: AppColors.surfaceBorder.withValues(alpha: 0.5),
        ),
      ),
      child: Row(
        children: [
          // Search icon
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
}
