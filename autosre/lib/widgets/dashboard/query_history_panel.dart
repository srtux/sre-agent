import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../services/saved_query_service.dart';
import '../../theme/app_theme.dart';

/// Overlay popup showing Recent and Saved query tabs for a given panel type.
///
/// Provides:
/// - **Recent** tab: auto-recorded query history (up to 1000 per panel)
/// - **Saved** tab: user-named bookmarked queries with save/delete
/// - Inline save dialog to bookmark a recent query
/// - Tap-to-use any query
class QueryHistoryPanel extends StatefulWidget {
  /// Panel type to scope queries: "logs", "metrics", "traces", "analytics".
  final String panelType;

  /// Called when the user taps a query to use it.
  final ValueChanged<String> onSelectQuery;

  /// Called to dismiss the overlay.
  final VoidCallback onDismiss;

  /// Current query text in the query bar (for quick-save).
  final String currentQuery;

  /// Current query language label.
  final String language;

  const QueryHistoryPanel({
    super.key,
    required this.panelType,
    required this.onSelectQuery,
    required this.onDismiss,
    this.currentQuery = '',
    this.language = '',
  });

  @override
  State<QueryHistoryPanel> createState() => _QueryHistoryPanelState();
}

class _QueryHistoryPanelState extends State<QueryHistoryPanel>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final _saveNameController = TextEditingController();
  bool _showSaveDialog = false;
  String _queryToSave = '';
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _saveNameController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final svc = SavedQueryService.instance;
    await Future.wait([
      svc.fetchRecentQueries(widget.panelType),
      svc.fetchSavedQueries(widget.panelType),
    ]);
    if (mounted) setState(() => _isLoading = false);
  }

  void _showSaveDialogFor(String query) {
    setState(() {
      _showSaveDialog = true;
      _queryToSave = query;
      _saveNameController.clear();
    });
  }

  Future<void> _saveQuery() async {
    final name = _saveNameController.text.trim();
    if (name.isEmpty) return;

    await SavedQueryService.instance.saveQuery(
      name: name,
      query: _queryToSave,
      panelType: widget.panelType,
      language: widget.language,
    );
    if (mounted) {
      setState(() => _showSaveDialog = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Container(
        width: 480,
        constraints: const BoxConstraints(maxHeight: 420),
        decoration: BoxDecoration(
          color: AppColors.backgroundCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: AppColors.surfaceBorder.withValues(alpha: 0.5),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.4),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildHeader(),
            if (_showSaveDialog) _buildSaveDialog(),
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.all(24),
                child: Center(
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: AppColors.primaryCyan,
                    ),
                  ),
                ),
              )
            else
              Flexible(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildRecentTab(),
                    _buildSavedTab(),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 8, 0),
          child: Row(
            children: [
              const Icon(Icons.history_rounded, size: 16, color: AppColors.primaryCyan),
              const SizedBox(width: 8),
              Text(
                'Query History',
                style: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const Spacer(),
              // Save current query button
              if (widget.currentQuery.trim().isNotEmpty)
                Tooltip(
                  message: 'Save current query',
                  child: IconButton(
                    icon: const Icon(Icons.bookmark_add_outlined, size: 16),
                    color: AppColors.warning,
                    onPressed: () => _showSaveDialogFor(widget.currentQuery),
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    padding: EdgeInsets.zero,
                  ),
                ),
              IconButton(
                icon: const Icon(Icons.close_rounded, size: 16),
                color: AppColors.textMuted,
                onPressed: widget.onDismiss,
                constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                padding: EdgeInsets.zero,
              ),
            ],
          ),
        ),
        TabBar(
          controller: _tabController,
          labelColor: AppColors.primaryCyan,
          unselectedLabelColor: AppColors.textMuted,
          labelStyle: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600),
          unselectedLabelStyle: GoogleFonts.inter(fontSize: 12),
          indicatorColor: AppColors.primaryCyan,
          indicatorSize: TabBarIndicatorSize.label,
          dividerColor: AppColors.surfaceBorder.withValues(alpha: 0.3),
          tabs: [
            Tab(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.schedule_rounded, size: 14),
                  const SizedBox(width: 6),
                  ListenableBuilder(
                    listenable: SavedQueryService.instance,
                    builder: (context, _) {
                      final count = SavedQueryService.instance
                          .getRecentQueries(widget.panelType)
                          .length;
                      return Text('Recent${count > 0 ? ' ($count)' : ''}');
                    },
                  ),
                ],
              ),
            ),
            Tab(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.bookmark_rounded, size: 14),
                  const SizedBox(width: 6),
                  ListenableBuilder(
                    listenable: SavedQueryService.instance,
                    builder: (context, _) {
                      final count = SavedQueryService.instance
                          .getSavedQueries(widget.panelType)
                          .length;
                      return Text('Saved${count > 0 ? ' ($count)' : ''}');
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSaveDialog() {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.backgroundDark,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: AppColors.warning.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Save Query',
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: AppColors.warning,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            _queryToSave.length > 80
                ? '${_queryToSave.substring(0, 80)}...'
                : _queryToSave,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 10,
              color: AppColors.textMuted,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 30,
                  child: TextField(
                    controller: _saveNameController,
                    autofocus: true,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: AppColors.textPrimary,
                    ),
                    decoration: InputDecoration(
                      hintText: 'Query name...',
                      hintStyle: GoogleFonts.inter(
                        fontSize: 12,
                        color: AppColors.textMuted.withValues(alpha: 0.6),
                      ),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide: BorderSide(
                          color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                        ),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide: BorderSide(
                          color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                        ),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide: const BorderSide(color: AppColors.primaryCyan),
                      ),
                      contentPadding:
                          const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      isDense: true,
                    ),
                    onSubmitted: (_) => _saveQuery(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                height: 30,
                child: TextButton(
                  onPressed: _saveQuery,
                  style: TextButton.styleFrom(
                    foregroundColor: AppColors.backgroundDark,
                    backgroundColor: AppColors.warning,
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                    ),
                    textStyle: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  child: const Text('Save'),
                ),
              ),
              const SizedBox(width: 4),
              SizedBox(
                height: 30,
                child: TextButton(
                  onPressed: () => setState(() => _showSaveDialog = false),
                  style: TextButton.styleFrom(
                    foregroundColor: AppColors.textMuted,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                    ),
                    textStyle: GoogleFonts.inter(fontSize: 11),
                  ),
                  child: const Text('Cancel'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildRecentTab() {
    return ListenableBuilder(
      listenable: SavedQueryService.instance,
      builder: (context, _) {
        final queries =
            SavedQueryService.instance.getRecentQueries(widget.panelType);
        if (queries.isEmpty) {
          return _buildEmptyState(
            icon: Icons.schedule_rounded,
            message: 'No recent queries yet',
            hint: 'Queries you run will appear here automatically.',
          );
        }
        return ListView.builder(
          padding: const EdgeInsets.symmetric(vertical: 4),
          itemCount: queries.length,
          itemBuilder: (context, index) {
            final q = queries[index];
            return _buildQueryTile(
              query: q.query,
              subtitle: _formatTimestamp(q.timestamp),
              languageLabel: q.language,
              onTap: () {
                widget.onSelectQuery(q.query);
                widget.onDismiss();
              },
              trailing: IconButton(
                icon: const Icon(Icons.bookmark_add_outlined, size: 14),
                color: AppColors.textMuted,
                onPressed: () => _showSaveDialogFor(q.query),
                constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                padding: EdgeInsets.zero,
                tooltip: 'Save this query',
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildSavedTab() {
    return ListenableBuilder(
      listenable: SavedQueryService.instance,
      builder: (context, _) {
        final queries =
            SavedQueryService.instance.getSavedQueries(widget.panelType);
        if (queries.isEmpty) {
          return _buildEmptyState(
            icon: Icons.bookmark_rounded,
            message: 'No saved queries yet',
            hint: 'Click the bookmark icon on any query to save it.',
          );
        }
        return ListView.builder(
          padding: const EdgeInsets.symmetric(vertical: 4),
          itemCount: queries.length,
          itemBuilder: (context, index) {
            final q = queries[index];
            return _buildQueryTile(
              query: q.query,
              subtitle: q.name ?? 'Unnamed',
              isSaved: true,
              languageLabel: q.language,
              onTap: () {
                widget.onSelectQuery(q.query);
                widget.onDismiss();
              },
              trailing: IconButton(
                icon: const Icon(Icons.delete_outline_rounded, size: 14),
                color: AppColors.error.withValues(alpha: 0.6),
                onPressed: () {
                  if (q.id != null) {
                    SavedQueryService.instance
                        .deleteSavedQuery(q.id!, widget.panelType);
                  }
                },
                constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                padding: EdgeInsets.zero,
                tooltip: 'Remove',
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildQueryTile({
    required String query,
    required String subtitle,
    required VoidCallback onTap,
    Widget? trailing,
    bool isSaved = false,
    String? languageLabel,
  }) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        child: Row(
          children: [
            Icon(
              isSaved ? Icons.bookmark_rounded : Icons.subdirectory_arrow_right_rounded,
              size: 14,
              color: isSaved ? AppColors.warning : AppColors.textMuted,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (isSaved)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 2),
                      child: Text(
                        subtitle,
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  Text(
                    query,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11,
                      color: isSaved
                          ? AppColors.textSecondary
                          : AppColors.textPrimary,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (!isSaved)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Row(
                        children: [
                          if (languageLabel != null && languageLabel.isNotEmpty) ...[
                            Container(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                              decoration: BoxDecoration(
                                color:
                                    AppColors.primaryCyan.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(3),
                              ),
                              child: Text(
                                languageLabel,
                                style: GoogleFonts.jetBrainsMono(
                                  fontSize: 9,
                                  color: AppColors.primaryCyan,
                                ),
                              ),
                            ),
                            const SizedBox(width: 6),
                          ],
                          Text(
                            subtitle,
                            style: GoogleFonts.inter(
                              fontSize: 10,
                              color: AppColors.textMuted,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            ?trailing,
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState({
    required IconData icon,
    required String message,
    required String hint,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 32, color: AppColors.textMuted.withValues(alpha: 0.4)),
            const SizedBox(height: 12),
            Text(
              message,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              hint,
              style: GoogleFonts.inter(
                fontSize: 11,
                color: AppColors.textMuted,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  String _formatTimestamp(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    try {
      final dt = DateTime.parse(iso);
      final now = DateTime.now().toUtc();
      final diff = now.difference(dt);
      if (diff.inMinutes < 1) return 'just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays < 7) return '${diff.inDays}d ago';
      return '${dt.month}/${dt.day}/${dt.year}';
    } catch (_) {
      return '';
    }
  }
}
