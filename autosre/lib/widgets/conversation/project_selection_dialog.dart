import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../services/project_service.dart';
import '../../theme/app_theme.dart';

/// Modal dialog shown when no previously-saved project is found.
///
/// Presents the user's accessible GCP projects in a searchable list
/// and requires selection before the dashboard can be populated.
class ProjectSelectionDialog extends StatefulWidget {
  final ProjectService projectService;
  final VoidCallback onProjectSelected;

  const ProjectSelectionDialog({
    super.key,
    required this.projectService,
    required this.onProjectSelected,
  });

  @override
  State<ProjectSelectionDialog> createState() => _ProjectSelectionDialogState();
}

class _ProjectSelectionDialogState extends State<ProjectSelectionDialog> {
  String _searchQuery = '';

  List<GcpProject> get _filteredProjects {
    final projects = widget.projectService.projects.value;
    if (_searchQuery.isEmpty) return projects;
    final query = _searchQuery.toLowerCase();
    return projects
        .where(
          (p) =>
              p.projectId.toLowerCase().contains(query) ||
              (p.displayName?.toLowerCase().contains(query) ?? false),
        )
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.backgroundCard,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480, maxHeight: 520),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppColors.primaryCyan.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.cloud_outlined,
                      size: 20,
                      color: AppColors.primaryCyan,
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Select a GCP Project',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        SizedBox(height: 2),
                        Text(
                          'Choose a project to start investigating',
                          style: TextStyle(
                            fontSize: 13,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Search field
              TextField(
                autofocus: true,
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 13,
                  color: AppColors.textPrimary,
                ),
                decoration: InputDecoration(
                  hintText: 'Search projects...',
                  hintStyle: TextStyle(
                    fontSize: 13,
                    color: AppColors.textMuted.withValues(alpha: 0.6),
                  ),
                  prefixIcon: Icon(
                    Icons.search_rounded,
                    size: 18,
                    color: AppColors.textMuted.withValues(alpha: 0.6),
                  ),
                  filled: true,
                  fillColor: AppColors.backgroundDark,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: BorderSide(
                      color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                    ),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: BorderSide(
                      color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                    ),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: const BorderSide(color: AppColors.primaryCyan),
                  ),
                ),
                onChanged: (value) => setState(() => _searchQuery = value),
              ),
              const SizedBox(height: 12),

              // Project list
              Expanded(
                child: ValueListenableBuilder<bool>(
                  valueListenable:
                      widget.projectService.isLoading as ValueNotifier<bool>,
                  builder: (context, isLoading, _) {
                    if (isLoading) {
                      return const Center(
                        child: CircularProgressIndicator(
                          color: AppColors.primaryCyan,
                        ),
                      );
                    }

                    final projects = _filteredProjects;
                    if (projects.isEmpty) {
                      return Center(
                        child: Text(
                          _searchQuery.isEmpty
                              ? 'No projects found'
                              : 'No matching projects',
                          style: const TextStyle(
                            fontSize: 13,
                            color: AppColors.textMuted,
                          ),
                        ),
                      );
                    }

                    return ListView.builder(
                      itemCount: projects.length,
                      itemBuilder: (context, index) {
                        final project = projects[index];
                        return _ProjectTile(
                          project: project,
                          onTap: () {
                            widget.projectService
                                .selectProjectInstance(project);
                            widget.onProjectSelected();
                            Navigator.of(context).pop();
                          },
                        );
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProjectTile extends StatefulWidget {
  final GcpProject project;
  final VoidCallback onTap;

  const _ProjectTile({required this.project, required this.onTap});

  @override
  State<_ProjectTile> createState() => _ProjectTileState();
}

class _ProjectTileState extends State<_ProjectTile> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: InkWell(
        onTap: widget.onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          margin: const EdgeInsets.only(bottom: 4),
          decoration: BoxDecoration(
            color: _isHovered
                ? AppColors.primaryCyan.withValues(alpha: 0.08)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: _isHovered
                  ? AppColors.primaryCyan.withValues(alpha: 0.3)
                  : AppColors.surfaceBorder.withValues(alpha: 0.2),
            ),
          ),
          child: Row(
            children: [
              Icon(
                Icons.cloud_outlined,
                size: 16,
                color: _isHovered
                    ? AppColors.primaryCyan
                    : AppColors.textMuted.withValues(alpha: 0.7),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.project.displayName ?? widget.project.projectId,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        color: _isHovered
                            ? AppColors.textPrimary
                            : AppColors.textSecondary,
                      ),
                    ),
                    if (widget.project.displayName != null &&
                        widget.project.displayName != widget.project.projectId)
                      Text(
                        widget.project.projectId,
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 11,
                          color: AppColors.textMuted,
                        ),
                      ),
                  ],
                ),
              ),
              if (_isHovered)
                const Icon(
                  Icons.arrow_forward_ios_rounded,
                  size: 12,
                  color: AppColors.primaryCyan,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
