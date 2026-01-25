import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/connectivity_service.dart';
import '../services/session_service.dart';
import '../theme/app_theme.dart';

/// A side panel that displays session history and allows navigation between sessions.
class SessionPanel extends StatefulWidget {
  final SessionService sessionService;
  final VoidCallback onNewSession;
  final ValueChanged<String> onSessionSelected;
  final String? currentSessionId;

  const SessionPanel({
    super.key,
    required this.sessionService,
    required this.onNewSession,
    required this.onSessionSelected,
    this.currentSessionId,
  });

  @override
  State<SessionPanel> createState() => _SessionPanelState();
}

class _SessionPanelState extends State<SessionPanel> {
  @override
  void initState() {
    super.initState();
    // Fetch sessions on mount
    widget.sessionService.fetchHistory();

    // Listen for connectivity changes to auto-refetch
    final connectivityService = Provider.of<ConnectivityService>(
      context,
      listen: false,
    );
    connectivityService.status.addListener(_onConnectivityChanged);
  }

  @override
  void dispose() {
    final connectivityService = Provider.of<ConnectivityService>(
      context,
      listen: false,
    );
    connectivityService.status.removeListener(_onConnectivityChanged);
    super.dispose();
  }

  void _onConnectivityChanged() {
    final connectivityStatus = Provider.of<ConnectivityService>(
      context,
      listen: false,
    ).status.value;
    if (connectivityStatus == ConnectivityStatus.connected &&
        widget.sessionService.sessions.value.isEmpty) {
      widget.sessionService.fetchHistory();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 280,
      decoration: const BoxDecoration(
        color: AppColors.backgroundCard,
        border: Border(
          right: BorderSide(color: AppColors.surfaceBorder, width: 1),
        ),
      ),
      child: Column(
        children: [
          // Header
          _buildHeader(),
          // Session list
          Expanded(child: _buildSessionList()),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
      decoration: const BoxDecoration(
        color: AppColors.backgroundCard,
        border: Border(
          // Removed bottom border for cleaner look, visual separation via spacing
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // "New Investigation" button as primary action
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: widget.onNewSession,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('New Investigation'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primaryTeal,
                foregroundColor: AppColors.backgroundDark,
                elevation: 0,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                textStyle: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              const Text(
                'Recent Investigations',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textMuted,
                  letterSpacing: 1.0,
                ),
              ),
              const Spacer(),
              // Loading indicator (replacing refresh button)
              ValueListenableBuilder<bool>(
                valueListenable: widget.sessionService.isLoading,
                builder: (context, isLoading, _) {
                  if (!isLoading) return const SizedBox.shrink();
                  return SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        AppColors.textMuted.withValues(alpha: 0.5),
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSessionList() {
    return ValueListenableBuilder<bool>(
      valueListenable: widget.sessionService.isLoading,
      builder: (context, isLoading, _) {
        return Column(
          children: [
            Expanded(
              child: ValueListenableBuilder<String?>(
                valueListenable: widget.sessionService.error,
                builder: (context, error, _) {
                  if (error != null && !isLoading) {
                    return Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(
                              Icons.error_outline,
                              color: AppColors.error,
                              size: 32,
                            ),
                            const SizedBox(height: 12),
                            const Text(
                              'Failed to load history',
                              style: TextStyle(
                                color: AppColors.error,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            const SizedBox(height: 8),
                            TextButton(
                              onPressed: () async {
                                // Set loading to true immediately for better UX
                                await widget.sessionService.fetchHistory(
                                  force: true,
                                );
                              },
                              child: const Text(
                                'Retry',
                                style: TextStyle(color: AppColors.primaryTeal),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }

                  final connectivityStatus = Provider.of<ConnectivityService>(
                    context,
                  ).status.value;
                  if (connectivityStatus == ConnectivityStatus.offline) {
                    return Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(
                              Icons.wifi_off,
                              color: AppColors.textMuted,
                              size: 32,
                            ),
                            const SizedBox(height: 12),
                            const Text(
                              'You are offline',
                              style: TextStyle(
                                color: AppColors.textMuted,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'History unavailable',
                              style: TextStyle(
                                color: AppColors.textMuted.withValues(
                                  alpha: 0.7,
                                ),
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                    );
                  }

                  return ValueListenableBuilder<List<SessionSummary>>(
                    valueListenable: widget.sessionService.sessions,
                    builder: (context, sessions, _) {
                      if (sessions.isEmpty && !isLoading) {
                        return _buildEmptyState();
                      }

                      if (sessions.isEmpty && isLoading) {
                        // Show nothing or a skeleton while initial load happens
                        return const SizedBox.shrink();
                      }

                      return ListView.builder(
                        padding: const EdgeInsets.symmetric(
                          vertical: 8,
                          horizontal: 8,
                        ),
                        itemCount: sessions.length,
                        itemBuilder: (context, index) {
                          final session = sessions[index];
                          final isSelected =
                              session.id == widget.currentSessionId;

                          return _SessionItem(
                            key: ValueKey(session.id),
                            session: session,
                            isSelected: isSelected,
                            onTap: () => widget.onSessionSelected(session.id),
                            onDelete: () => _deleteSession(session.id),
                            onRename: () => _renameSession(
                              session.id,
                              session.displayTitle,
                            ),
                          );
                        },
                      );
                    },
                  );
                },
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.explore_outlined,
              size: 48,
              color: AppColors.textMuted.withValues(alpha: 0.3),
            ),
            const SizedBox(height: 16),
            const Text(
              'No investigations yet',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: AppColors.textMuted,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Start a new investigation to analyze your GCP telemetry',
              style: TextStyle(
                fontSize: 12,
                color: AppColors.textMuted.withValues(alpha: 0.7),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _deleteSession(String sessionId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.backgroundCard,
        title: const Text(
          'Delete Investigation',
          style: TextStyle(color: AppColors.textPrimary),
        ),
        content: const Text(
          'Are you sure you want to delete this investigation? This action cannot be undone.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel', style: TextStyle(color: AppColors.textMuted)),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await widget.sessionService.deleteSession(sessionId);
    }
  }

  Future<void> _renameSession(String sessionId, String currentTitle) async {
    final controller = TextEditingController(text: currentTitle);
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.backgroundCard,
        title: const Text(
          'Rename Investigation',
          style: TextStyle(color: AppColors.textPrimary),
        ),
        content: TextField(
          controller: controller,
          autofocus: true,
          style: const TextStyle(color: AppColors.textPrimary),
          decoration: const InputDecoration(
            hintText: 'Enter new name',
            hintStyle: TextStyle(color: AppColors.textMuted),
            enabledBorder: UnderlineInputBorder(
              borderSide: BorderSide(color: AppColors.surfaceBorder),
            ),
            focusedBorder: UnderlineInputBorder(
              borderSide: BorderSide(color: AppColors.primaryTeal),
            ),
          ),
          onSubmitted: (_) {
            if (controller.text.trim().isNotEmpty) {
              widget.sessionService.renameSession(
                sessionId,
                controller.text.trim(),
              );
              Navigator.of(context).pop();
            }
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel', style: TextStyle(color: AppColors.textMuted)),
          ),
          TextButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                widget.sessionService.renameSession(
                  sessionId,
                  controller.text.trim(),
                );
                Navigator.of(context).pop();
              }
            },
            child: const Text(
              'Rename',
              style: TextStyle(color: AppColors.primaryTeal),
            ),
          ),
        ],
      ),
    );
  }
}

class _SessionItem extends StatefulWidget {
  final SessionSummary session;
  final bool isSelected;
  final VoidCallback onTap;
  final VoidCallback onDelete;
  final VoidCallback onRename;

  const _SessionItem({
    super.key,
    required this.session,
    required this.isSelected,
    required this.onTap,
    required this.onDelete,
    required this.onRename,
  });

  @override
  State<_SessionItem> createState() => _SessionItemState();
}

class _SessionItemState extends State<_SessionItem> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: widget.onTap,
            borderRadius: BorderRadius.circular(8),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: widget.isSelected
                    ? AppColors.primaryTeal.withValues(alpha: 0.15)
                    : _isHovered
                    ? Colors.white.withValues(alpha: 0.03)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  // Icon
                  Icon(
                    Icons.chat_bubble_outline,
                    size: 16,
                    color: widget.isSelected
                        ? AppColors.primaryTeal
                        : AppColors.textMuted,
                  ),
                  const SizedBox(width: 12),
                  // Content
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.session.displayTitle,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: widget.isSelected
                                ? FontWeight.w600
                                : FontWeight.w500,
                            color: widget.isSelected
                                ? AppColors.primaryTeal
                                : AppColors.textPrimary,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Text(
                              widget.session.formattedDate,
                              style: const TextStyle(
                                fontSize: 11,
                                color: AppColors.textMuted,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  // Actions (Edit/Delete) on hover
                  if (_isHovered) ...[
                    IconButton(
                      onPressed: widget.onRename,
                      icon: const Icon(
                        Icons.edit_outlined,
                        size: 14,
                        color: AppColors.textMuted,
                      ),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(
                        minWidth: 24,
                        minHeight: 24,
                      ),
                      tooltip: 'Rename',
                    ),
                    const SizedBox(width: 4),
                    IconButton(
                      onPressed: widget.onDelete,
                      icon: const Icon(
                        Icons.delete_outline,
                        size: 14,
                        color: AppColors.textMuted,
                      ),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(
                        minWidth: 24,
                        minHeight: 24,
                      ),
                      tooltip: 'Delete',
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
