import 'dart:async';
import 'package:flutter/material.dart';
import '../../services/project_service.dart';
import '../../theme/app_theme.dart';

/// Modern searchable project selector with combobox functionality.
class ProjectSelectorDropdown extends StatefulWidget {
  final List<GcpProject> projects;
  final List<GcpProject> recentProjects;
  final List<GcpProject> starredProjects;
  final GcpProject? selectedProject;
  final bool isLoading;
  final String? error;
  final ValueChanged<GcpProject?> onProjectSelected;
  final VoidCallback onRefresh;
  final ValueChanged<String> onSearch;
  final ValueChanged<GcpProject> onToggleStar;

  const ProjectSelectorDropdown({
    super.key,
    required this.projects,
    required this.recentProjects,
    required this.starredProjects,
    required this.selectedProject,
    required this.isLoading,
    this.error,
    required this.onProjectSelected,
    required this.onRefresh,
    required this.onSearch,
    required this.onToggleStar,
  });

  @override
  State<ProjectSelectorDropdown> createState() =>
      _ProjectSelectorDropdownState();
}

class _ProjectSelectorDropdownState extends State<ProjectSelectorDropdown>
    with SingleTickerProviderStateMixin {
  final LayerLink _layerLink = LayerLink();
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _searchFocusNode = FocusNode();
  OverlayEntry? _overlayEntry;
  bool _isOpen = false;
  String _searchQuery = '';
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;

  Timer? _debounceTimer;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    _fadeAnimation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeOut,
    );
    _scaleAnimation = Tween<double>(begin: 0.95, end: 1.0).animate(
      CurvedAnimation(
          parent: _animationController, curve: Curves.easeOutCubic),
    );
  }

  @override
  void didUpdateWidget(ProjectSelectorDropdown oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_isOpen) {
      _overlayEntry?.markNeedsBuild();
    }
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _animationController.dispose();
    if (_isOpen) {
      _overlayEntry?.remove();
      _overlayEntry = null;
    }
    _searchController.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  List<GcpProject> get _filteredProjects {
    return widget.projects;
  }

  void _toggleDropdown() {
    if (_isOpen) {
      _closeDropdown();
    } else {
      _openDropdown();
    }
  }

  void _openDropdown() {
    _overlayEntry = _createOverlayEntry();
    Overlay.of(context).insert(_overlayEntry!);
    _animationController.forward();
    setState(() {
      _isOpen = true;
    });
    Future.delayed(const Duration(milliseconds: 100), () {
      if (mounted) {
        _searchFocusNode.requestFocus();
      }
    });
  }

  void _closeDropdown() {
    _animationController.reverse().then((_) {
      if (mounted) {
        _overlayEntry?.remove();
        _overlayEntry = null;
      }
    });
    if (mounted) {
      setState(() {
        _isOpen = false;
        _searchQuery = '';
        _searchController.clear();
      });
      widget.onSearch('');
    }
  }

  void _selectCustomProject(String projectId) {
    if (projectId.trim().isEmpty) return;
    final customProject = GcpProject(projectId: projectId.trim());
    widget.onProjectSelected(customProject);
    _closeDropdown();
  }

  OverlayEntry _createOverlayEntry() {
    final renderBox = context.findRenderObject() as RenderBox;
    final size = renderBox.size;
    final offset = renderBox.localToGlobal(Offset.zero);

    return OverlayEntry(
      builder: (context) => GestureDetector(
        behavior: HitTestBehavior.translucent,
        onTap: _closeDropdown,
        child: Material(
          color: Colors.transparent,
          child: Stack(
            children: [
              Positioned(
                left: offset.dx,
                top: offset.dy + size.height + 8,
                width: 360,
                child: GestureDetector(
                  onTap: () {},
                  child: FadeTransition(
                    opacity: _fadeAnimation,
                    child: ScaleTransition(
                      scale: _scaleAnimation,
                      alignment: Alignment.topLeft,
                      child: _buildDropdownContent(),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDropdownContent() {
    return DefaultTabController(
      length: 2,
      child: StatefulBuilder(
        builder: (context, setDropdownState) {
          return Container(
            constraints: const BoxConstraints(maxHeight: 550),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: Colors.white.withValues(alpha: 0.1)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.4),
                  blurRadius: 24,
                  offset: const Offset(0, 12),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Search input
                  SizedBox(
                    height: 50,
                    child: TextField(
                      controller: _searchController,
                      focusNode: _searchFocusNode,
                      style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 14,
                      ),
                      decoration: InputDecoration(
                        hintText: 'Search or enter project ID...',
                        hintStyle: const TextStyle(
                          color: AppColors.textMuted,
                          fontSize: 13,
                        ),
                        prefixIcon: const Icon(
                          Icons.search,
                          size: 18,
                          color: AppColors.textMuted,
                        ),
                        suffixIcon: _searchController.text.isNotEmpty
                            ? IconButton(
                                icon: const Icon(
                                  Icons.clear,
                                  size: 16,
                                  color: AppColors.textMuted,
                                ),
                                onPressed: () {
                                  _searchController.clear();
                                  setDropdownState(() {
                                    _searchQuery = '';
                                  });
                                  widget.onSearch('');
                                },
                              )
                            : null,
                        border: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        errorBorder: InputBorder.none,
                        disabledBorder: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 15,
                        ),
                      ),
                      onChanged: (value) {
                        setDropdownState(() {
                          _searchQuery = value;
                        });
                        _debounceTimer?.cancel();
                        _debounceTimer = Timer(
                          const Duration(milliseconds: 500),
                          () {
                            widget.onSearch(value);
                          },
                        );
                      },
                      onSubmitted: (value) {
                        if (_filteredProjects.isEmpty && value.isNotEmpty) {
                          _selectCustomProject(value);
                        } else if (_filteredProjects.length == 1) {
                          widget.onProjectSelected(_filteredProjects.first);
                          _closeDropdown();
                        }
                      },
                    ),
                  ),
                  const Divider(height: 1, color: Colors.white10),

                  // Header with refresh and project count
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.02),
                    ),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(
                            color:
                                AppColors.primaryTeal.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Icon(
                            Icons.cloud_outlined,
                            size: 14,
                            color: AppColors.primaryTeal,
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Text(
                          'GCP Projects',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textMuted,
                            letterSpacing: 0.5,
                          ),
                        ),
                        const Spacer(),
                        if (_searchQuery.isNotEmpty)
                          Text(
                            '${_filteredProjects.length} matches',
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.textMuted,
                            ),
                          )
                        else
                          Text(
                            '${widget.projects.length} total',
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.textMuted,
                            ),
                          ),
                        const SizedBox(width: 8),
                        Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: widget.onRefresh,
                            borderRadius: BorderRadius.circular(6),
                            child: Padding(
                              padding: const EdgeInsets.all(6),
                              child: widget.isLoading
                                  ? const SizedBox(
                                      width: 14,
                                      height: 14,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        valueColor:
                                            AlwaysStoppedAnimation<Color>(
                                          AppColors.primaryTeal,
                                        ),
                                      ),
                                    )
                                  : const Icon(
                                      Icons.refresh,
                                      size: 14,
                                      color: AppColors.textMuted,
                                    ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Tab Bar for Favorites/Recent vs All
                  if (_searchQuery.isEmpty)
                    const TabBar(
                      indicatorColor: AppColors.primaryTeal,
                      indicatorSize: TabBarIndicatorSize.tab,
                      labelColor: AppColors.primaryTeal,
                      unselectedLabelColor: AppColors.textMuted,
                      labelStyle: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                      ),
                      tabs: [
                        Tab(text: 'FAVORITES & RECENT'),
                        Tab(text: 'ALL PROJECTS'),
                      ],
                    ),

                  // Tab Content
                  Flexible(
                    child: _searchQuery.isNotEmpty
                        ? _buildSearchResults(setDropdownState)
                        : TabBarView(
                            children: [
                              _buildFavoritesAndRecentTab(),
                              _buildAllProjectsTab(),
                            ],
                          ),
                  ),

                  if (_searchQuery.isNotEmpty && _filteredProjects.isEmpty)
                    _buildUseCustomProjectOption(
                        _searchQuery, setDropdownState),

                  if (_searchQuery.isNotEmpty && _filteredProjects.isNotEmpty)
                    _buildUseCustomProjectOption(
                        _searchQuery, setDropdownState),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildSearchResults(StateSetter setDropdownState) {
    if (widget.isLoading) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: 32),
          child: SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor:
                  AlwaysStoppedAnimation<Color>(AppColors.primaryTeal),
            ),
          ),
        ),
      );
    }

    if (_filteredProjects.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(Icons.search_off, size: 32, color: AppColors.textMuted),
            SizedBox(height: 12),
            Text(
              'No matching projects',
              style: TextStyle(fontSize: 13, color: AppColors.textMuted),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      padding: const EdgeInsets.symmetric(vertical: 4),
      itemCount: _filteredProjects.length,
      itemBuilder: (context, index) {
        final project = _filteredProjects[index];
        final isSelected =
            widget.selectedProject?.projectId == project.projectId;
        return _buildProjectItem(project, isSelected);
      },
    );
  }

  Widget _buildFavoritesAndRecentTab() {
    if (widget.error != null) return _buildErrorState();
    if (widget.starredProjects.isEmpty && widget.recentProjects.isEmpty) {
      return _buildEmptyState('No favorites or recent projects');
    }

    return ListView(
      padding: const EdgeInsets.symmetric(vertical: 4),
      children: [
        if (widget.starredProjects.isNotEmpty) ...[
          _buildSectionHeader(Icons.star, 'STARRED', Colors.amber),
          ...widget.starredProjects.map((project) {
            final isSelected =
                widget.selectedProject?.projectId == project.projectId;
            return _buildProjectItem(project, isSelected);
          }),
          const Divider(height: 16, color: Colors.white10),
        ],
        if (widget.recentProjects.isNotEmpty) ...[
          _buildSectionHeader(
              Icons.history, 'RECENT', AppColors.primaryTeal),
          ...widget.recentProjects.map((project) {
            final isSelected =
                widget.selectedProject?.projectId == project.projectId;
            return _buildProjectItem(project, isSelected);
          }),
        ],
      ],
    );
  }

  Widget _buildAllProjectsTab() {
    if (widget.error != null) return _buildErrorState();
    if (widget.projects.isEmpty) {
      return _buildEmptyState('No projects available');
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: 4),
      itemCount: widget.projects.length,
      itemBuilder: (context, index) {
        final project = widget.projects[index];
        final isSelected =
            widget.selectedProject?.projectId == project.projectId;
        return _buildProjectItem(project, isSelected);
      },
    );
  }

  Widget _buildSectionHeader(IconData icon, String title, Color iconColor) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
      child: Row(
        children: [
          Icon(icon, size: 12, color: iconColor.withValues(alpha: 0.8)),
          const SizedBox(width: 6),
          Text(
            title,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: AppColors.textMuted.withValues(alpha: 0.7),
              letterSpacing: 0.8,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline,
              size: 32, color: Colors.redAccent),
          const SizedBox(height: 12),
          const Text(
            'Error loading projects',
            style: TextStyle(
              fontSize: 13,
              color: Colors.redAccent,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            widget.error!,
            textAlign: TextAlign.center,
            style:
                const TextStyle(fontSize: 11, color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(String message) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.cloud_off_outlined,
              size: 32, color: AppColors.textMuted),
          const SizedBox(height: 12),
          Text(
            message,
            style:
                const TextStyle(fontSize: 13, color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }

  Widget _buildUseCustomProjectOption(
    String projectId,
    StateSetter setDropdownState,
  ) {
    final exactMatch =
        widget.projects.any((p) => p.projectId == projectId);
    if (exactMatch) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.fromLTRB(8, 4, 8, 8),
      decoration: BoxDecoration(
        color: AppColors.primaryTeal.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
            color: AppColors.primaryTeal.withValues(alpha: 0.3)),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _selectCustomProject(projectId),
          borderRadius: BorderRadius.circular(10),
          child: Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color:
                        AppColors.primaryTeal.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Icon(
                    Icons.add,
                    size: 14,
                    color: AppColors.primaryTeal,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Use "$projectId"',
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: AppColors.primaryTeal,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                      const Text(
                        'Press Enter or click to use this project ID',
                        style: TextStyle(
                          fontSize: 11,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.keyboard_return,
                  size: 14,
                  color: AppColors.primaryTeal,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildProjectItem(GcpProject project, bool isSelected) {
    final isStarred = widget.starredProjects
        .any((p) => p.projectId == project.projectId);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      child: Material(
        color: Colors.transparent,
        child: Row(
          children: [
            Expanded(
              child: InkWell(
                onTap: () {
                  widget.onProjectSelected(project);
                  _closeDropdown();
                },
                borderRadius: BorderRadius.circular(10),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 150),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? AppColors.primaryTeal.withValues(alpha: 0.15)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: isSelected
                          ? AppColors.primaryTeal.withValues(alpha: 0.3)
                          : Colors.transparent,
                    ),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          gradient: isSelected
                              ? LinearGradient(
                                  colors: [
                                    AppColors.primaryTeal
                                        .withValues(alpha: 0.3),
                                    AppColors.primaryCyan
                                        .withValues(alpha: 0.2),
                                  ],
                                )
                              : null,
                          color: isSelected
                              ? null
                              : Colors.white.withValues(alpha: 0.05),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Icon(
                          isSelected
                              ? Icons.folder
                              : Icons.folder_outlined,
                          size: 16,
                          color: isSelected
                              ? AppColors.primaryTeal
                              : AppColors.textMuted,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              project.name,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: isSelected
                                    ? FontWeight.w600
                                    : FontWeight.w500,
                                color: isSelected
                                    ? AppColors.primaryTeal
                                    : AppColors.textPrimary,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                            if (project.displayName != null &&
                                project.displayName != project.projectId)
                              Text(
                                project.projectId,
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: AppColors.textMuted,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => widget.onToggleStar(project),
                borderRadius: BorderRadius.circular(20),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Icon(
                    isStarred ? Icons.star : Icons.star_border,
                    size: 18,
                    color: isStarred
                        ? Colors.amber
                        : AppColors.textMuted.withValues(alpha: 0.4),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return CompositedTransformTarget(
      link: _layerLink,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: _toggleDropdown,
          borderRadius: BorderRadius.circular(6),
          child: Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            decoration: BoxDecoration(
              color: _isOpen
                  ? AppColors.primaryTeal.withValues(alpha: 0.1)
                  : Colors.white.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: _isOpen
                    ? AppColors.primaryTeal.withValues(alpha: 0.3)
                    : AppColors.surfaceBorder.withValues(alpha: 0.5),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.folder_outlined,
                  size: 14,
                  color: _isOpen
                      ? AppColors.primaryTeal
                      : AppColors.textMuted,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    widget.selectedProject?.name ?? 'Project',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: widget.selectedProject != null
                          ? AppColors.textPrimary
                          : AppColors.textMuted,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 2),
                AnimatedRotation(
                  turns: _isOpen ? 0.5 : 0,
                  duration: const Duration(milliseconds: 150),
                  child: Icon(
                    Icons.keyboard_arrow_down,
                    size: 16,
                    color: _isOpen
                        ? AppColors.primaryTeal
                        : AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
