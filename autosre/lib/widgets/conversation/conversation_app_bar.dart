import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../agent/adk_content_generator.dart';
import '../../services/auth_service.dart';
import '../../services/project_service.dart';
import '../../services/version_service.dart';
import '../../theme/app_theme.dart';
import '../../services/session_service.dart';
import '../../pages/tool_config_page.dart';
import '../../pages/help_page.dart';
import 'project_selector.dart';

/// The app bar for the conversation page, containing logo, project selector,
/// status indicator, trace link, settings, help, history, and user profile.
class ConversationAppBar extends StatelessWidget
    implements PreferredSizeWidget {
  final bool isMobile;
  final ADKContentGenerator? contentGenerator;
  final ProjectService projectService;
  final SessionService sessionService;
  final String? currentTraceUrl;
  final String? currentTraceId;
  final VoidCallback onStartNewSession;
  final ValueChanged<String> onLoadSession;
  final bool isChatOpen;
  final VoidCallback onToggleChat;

  const ConversationAppBar({
    super.key,
    required this.isMobile,
    required this.contentGenerator,
    required this.projectService,
    required this.sessionService,
    this.currentTraceUrl,
    this.currentTraceId,
    required this.onStartNewSession,
    required this.onLoadSession,
    this.isChatOpen = true,
    required this.onToggleChat,
  });

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      backgroundColor: AppColors.backgroundCard,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shape: Border(
        bottom: BorderSide(
          color: AppColors.surfaceBorder.withValues(alpha: 0.5),
          width: 1,
        ),
      ),
      leading: null,
      automaticallyImplyLeading: false,
      titleSpacing: 0,
      title: LayoutBuilder(
        builder: (context, constraints) {
          final isCompact = constraints.maxWidth < 600;
          return Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              _LogoButton(onTap: onStartNewSession),
              const SizedBox(width: 8),
              if (!isCompact) ...[
                InkWell(
                  onTap: onStartNewSession,
                  child: Stack(
                    children: [
                      Text(
                        'AutoSRE',
                        style: GoogleFonts.inter(
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                          color: Colors.transparent,
                          letterSpacing: 0.5,
                          shadows: [
                            const Shadow(
                              color: Colors.blueAccent,
                              blurRadius: 10,
                              offset: Offset(0, 0),
                            ),
                          ],
                        ),
                      ),
                      ShaderMask(
                        shaderCallback: (bounds) => const LinearGradient(
                          colors: [Colors.white, AppColors.primaryCyan],
                          begin: Alignment.centerLeft,
                          end: Alignment.centerRight,
                        ).createShader(bounds),
                        child: Text(
                          'AutoSRE',
                          style: GoogleFonts.inter(
                            fontSize: 20,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 24),
              ],
              Flexible(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 250),
                  child: _buildProjectSelector(),
                ),
              ),
            ],
          );
        },
      ),
      actions: [
        if (!isChatOpen)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Tooltip(
              message: 'Open Conversation',
              child: IconButton(
                icon: const Icon(Icons.chat, color: AppColors.textSecondary),
                onPressed: onToggleChat,
              ),
            ),
          ),
        if (currentTraceUrl != null)
          _ViewTraceChip(
            traceId: currentTraceId ?? '',
            traceUrl: currentTraceUrl!,
          ),
        // Status indicator
        ValueListenableBuilder<bool>(
          valueListenable:
              contentGenerator?.isConnected ?? ValueNotifier(false),
          builder: (context, isConnected, _) {
            return ValueListenableBuilder<bool>(
              valueListenable:
                  contentGenerator?.isProcessing ?? ValueNotifier(false),
              builder: (context, isProcessing, _) {
                return _StatusIndicator(
                  isConnected: isConnected,
                  agentUrl: contentGenerator?.baseUrl ?? '',
                );
              },
            );
          },
        ),
        const SizedBox(width: 12),
        _SettingsButton(),
        const SizedBox(width: 8),
        IconButton(
          icon: const Icon(Icons.help_outline, color: AppColors.textSecondary),
          tooltip: 'Help & Documentation',
          onPressed: () {
            Navigator.of(
              context,
            ).push(MaterialPageRoute(builder: (context) => const HelpPage()));
          },
        ),
        const SizedBox(width: 8),
        _UserProfileButton(),
        const SizedBox(width: 16),
      ],
    );
  }

  Widget _buildProjectSelector() {
    // Merge all project service notifiers into a single listenable to avoid
    // deeply nested ValueListenableBuilders (was 6 levels deep, causing O(n)
    // rebuild cascades on every notifier change).
    return ListenableBuilder(
      listenable: Listenable.merge([
        projectService.isLoading,
        projectService.projects,
        projectService.selectedProject,
        projectService.error,
        projectService.recentProjects,
        projectService.starredProjects,
      ]),
      builder: (context, _) {
        return ProjectSelectorDropdown(
          projects: projectService.projects.value,
          recentProjects: projectService.recentProjects.value,
          starredProjects: projectService.starredProjects.value,
          selectedProject: projectService.selectedProject.value,
          isLoading: projectService.isLoading.value,
          error: projectService.error.value,
          onProjectSelected: (project) {
            projectService.selectProjectInstance(project);
          },
          onRefresh: () {
            projectService.fetchProjects();
          },
          onSearch: (query) {
            projectService.fetchProjects(query: query);
          },
          onToggleStar: (project) {
            projectService.toggleStar(project);
          },
        );
      },
    );
  }
}

class _LogoButton extends StatelessWidget {
  final VoidCallback onTap;

  const _LogoButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: 'New Session',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: const Padding(
            padding: EdgeInsets.all(8),
            child: Icon(
              Icons.smart_toy,
              color: AppColors.primaryTeal,
              size: 32,
            ),
          ),
        ),
      ),
    );
  }
}

class _ViewTraceChip extends StatelessWidget {
  final String traceId;
  final String traceUrl;

  const _ViewTraceChip({required this.traceId, required this.traceUrl});

  @override
  Widget build(BuildContext context) {
    final shortId = traceId.length > 8 ? traceId.substring(0, 8) : traceId;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Tooltip(
        message: 'View agent reasoning trace in Cloud Trace\nTrace: $traceId',
        child: ActionChip(
          avatar: Icon(
            Icons.timeline_rounded,
            size: 14,
            color: AppColors.primaryCyan.withValues(alpha: 0.9),
          ),
          label: Text(
            'Trace $shortId',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              color: AppColors.primaryCyan,
              fontWeight: FontWeight.w500,
            ),
          ),
          side: BorderSide(color: AppColors.primaryCyan.withValues(alpha: 0.3)),
          backgroundColor: AppColors.primaryCyan.withValues(alpha: 0.08),
          onPressed: () async {
            final uri = Uri.parse(traceUrl);
            if (await canLaunchUrl(uri)) {
              await launchUrl(uri, mode: LaunchMode.externalApplication);
            }
          },
        ),
      ),
    );
  }
}

class _SettingsButton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: 'Settings',
      child: IconButton(
        icon: const Icon(
          Icons.settings_outlined,
          color: AppColors.textSecondary,
        ),
        onPressed: () {
          Navigator.of(context).push(
            MaterialPageRoute(builder: (context) => const ToolConfigPage()),
          );
        },
      ),
    );
  }
}

class _StatusIndicator extends StatelessWidget {
  final bool isConnected;
  final String agentUrl;

  const _StatusIndicator({required this.isConnected, required this.agentUrl});

  @override
  Widget build(BuildContext context) {
    final statusColor = isConnected ? AppColors.success : AppColors.error;
    final statusText = isConnected ? 'Connected' : 'Offline';

    return Tooltip(
      message:
          'Agent URL: ${agentUrl.isEmpty ? "Internal" : agentUrl}\nStatus: $statusText',
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: AppColors.backgroundDark,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder, width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      textStyle: const TextStyle(color: AppColors.textPrimary, fontSize: 12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: statusColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: statusColor,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              statusText,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: statusColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _UserProfileButton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final authService = Provider.of<AuthService>(context, listen: false);
    final user = authService.currentUser;
    final displayName = authService.isAuthEnabled
        ? (user?.displayName ?? 'User Profile')
        : 'Local Dev';
    final photoUrl = user?.photoUrl;
    final isDevMode = !authService.isAuthEnabled;

    return Tooltip(
      message: displayName,
      child: Material(
        color: Colors.transparent,
        shape: const CircleBorder(),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () {
            showDialog(
              context: context,
              builder: (context) => AlertDialog(
                title: Text(displayName),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (isDevMode)
                      const Padding(
                        padding: EdgeInsets.only(bottom: 8.0),
                        child: Text(
                          'Authentication is disabled in this environment (Local Dev Mode).',
                          style: TextStyle(
                            fontStyle: FontStyle.italic,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ),
                    if (user?.email != null) Text('Email: ${user!.email}'),
                    const SizedBox(height: 16),
                    const Divider(),
                    const SizedBox(height: 8),
                    Text(
                      'AutoSRE ${VersionService.instance.displayString}',
                      style: const TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 12,
                      ),
                    ),
                    if (VersionService.instance.buildTimestamp.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          'Built: ${VersionService.instance.buildTimestamp}',
                          style: const TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 11,
                          ),
                        ),
                      ),
                  ],
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Close'),
                  ),
                  if (authService.isAuthEnabled)
                    TextButton(
                      onPressed: () {
                        Navigator.pop(context);
                        authService.signOut();
                      },
                      child: const Text('Sign Out'),
                    ),
                ],
              ),
            );
          },
          child: CircleAvatar(
            radius: 16,
            backgroundColor: isDevMode
                ? AppColors.warning
                : AppColors.surfaceGlass,
            backgroundImage: photoUrl != null ? NetworkImage(photoUrl) : null,
            child: photoUrl == null
                ? Icon(
                    isDevMode ? Icons.developer_mode : Icons.person,
                    size: 20,
                    color: isDevMode ? Colors.white : AppColors.textSecondary,
                  )
                : null,
          ),
        ),
      ),
    );
  }
}
