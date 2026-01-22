import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter/rendering.dart';
import 'package:genui/genui.dart';
import 'package:provider/provider.dart';

import '../services/auth_service.dart';

import '../agent/adk_content_generator.dart';
import '../catalog.dart';
import '../services/project_service.dart';
import '../services/session_service.dart';
import '../theme/app_theme.dart';
import '../widgets/session_panel.dart';
import '../widgets/tech_grid_painter.dart';
import '../widgets/unified_prompt_input.dart';
import 'package:google_fonts/google_fonts.dart';
import 'tool_config_page.dart';
import '../widgets/status_toast.dart';
import '../widgets/glow_action_chip.dart';

class ConversationPage extends StatefulWidget {
  const ConversationPage({super.key});

  static const double kMaxContentWidth = 1000.0;

  @override
  State<ConversationPage> createState() => _ConversationPageState();
}

class _ConversationPageState extends State<ConversationPage>
    with TickerProviderStateMixin {
  late A2uiMessageProcessor _messageProcessor;
  late GenUiConversation _conversation;
  late ADKContentGenerator _contentGenerator;
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _focusNode = FocusNode();
  final ProjectService _projectService = ProjectService();
  final SessionService _sessionService = SessionService();
  final GlobalKey _inputKey = GlobalKey(debugLabel: 'prompt_input');

  late AnimationController _typingController;

  StreamSubscription<String>? _sessionSubscription;
  final ValueNotifier<List<String>> _suggestedActions = ValueNotifier([
    "Analyze last hour's logs",
    "List active incidents",
    "Check for high latency",
  ]);
  StreamSubscription<List<String>>? _suggestionsSubscription;

  @override
  void initState() {
    super.initState();

    // Handle Enter key behavior (Enter to send, Shift+Enter for newline)
    _focusNode.onKeyEvent = (node, event) {
      if (event is KeyDownEvent &&
          event.logicalKey == LogicalKeyboardKey.enter) {
        if (HardwareKeyboard.instance.isShiftPressed) {
          return KeyEventResult.ignored;
        }
        _sendMessage();
        return KeyEventResult.handled;
      }
      return KeyEventResult.ignored;
    };

    // Typing indicator animation
    _typingController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    )..repeat();

    _initializeConversation();

    // Session subscription is now handled in _initializeConversation to ensure it persists across resets

    // Fetch projects and sessions on startup
    _projectService.fetchProjects();
    _sessionService.fetchSessions();

    // Update content generator when project selection changes
    _projectService.selectedProject.addListener(_onProjectChanged);
  }

  void _initializeConversation() {
    final sreCatalog = CatalogRegistry.createSreCatalog();

    _messageProcessor = A2uiMessageProcessor(
      catalogs: [sreCatalog, CoreCatalogItems.asCatalog()],
    );

    // Dispose previous content generator if it exists (though effectively we just replace it)
    // We need to cancel the old subscription before creating a new one to avoid leaks/stale listeners
    _sessionSubscription?.cancel();

    _contentGenerator = ADKContentGenerator();
    _contentGenerator.projectId = _projectService.selectedProjectId;

    // Subscribe to the NEW session stream immediately
    _sessionSubscription = _contentGenerator.sessionStream.listen((sessionId) {
      _sessionService.setCurrentSession(sessionId);
      // Refresh sessions list after a message is sent creates a new session
      _sessionService.fetchSessions();
    });

    _conversation = GenUiConversation(
      a2uiMessageProcessor: _messageProcessor,
      contentGenerator: _contentGenerator,
      onSurfaceAdded: (update) => _scrollToBottom(force: true),
      onSurfaceUpdated: (update) => _scrollToBottom(),
      onTextResponse: (text) => _scrollToBottom(),
    );

    // Subscribe to suggestions
    _suggestionsSubscription = _contentGenerator.suggestionsStream.listen((
      suggestions,
    ) {
      if (mounted) {
        _suggestedActions.value = suggestions;
      }
    });

    // Initial fetch of suggestions
    _contentGenerator.fetchSuggestions();
  }

  void _onProjectChanged() {
    _contentGenerator.projectId = _projectService.selectedProjectId;
    _contentGenerator.fetchSuggestions();
  }

  void _startNewSession() {
    // Clear session in content generator (new messages will start a new backend session)
    _contentGenerator.clearSession();
    // Clear current session in service
    _sessionService.startNewSession();

    // Reset conversation state
    setState(() {
      _conversation.dispose();
      _initializeConversation();
    });

    // Show confirmation
    StatusToast.show(context, 'Starting new investigation...');
  }

  Future<void> _loadSession(String sessionId) async {
    // Load session from backend
    final session = await _sessionService.getSession(sessionId);
    if (session == null) {
      // ignore: use_build_context_synchronously
      if (mounted) {
        StatusToast.show(context, 'Failed to load session history');
      }
      return;
    }

    // Set session ID in content generator
    _contentGenerator.sessionId = sessionId;
    _sessionService.setCurrentSession(sessionId);

    if (!mounted) return;

    // Reset and hydrate conversation
    setState(() {
      _conversation.dispose();
      _initializeConversation();
    });

    // Hydrate history if available
    if (session.messages.isNotEmpty) {
      final history = <ChatMessage>[];
      for (final msg in session.messages) {
        if (msg.role == 'user' || msg.role == 'human') {
          history.add(UserMessage.text(msg.content));
        } else {
          // Default to AiTextMessage for model responses in history
          // (Original UI events are not preserved in text-only history yet)
          history.add(AiTextMessage([TextPart(msg.content)]));
        }
      }

      // Inject history into conversation state
      // Note: Cast to ValueNotifier to update state directly
      try {
        if (_conversation.conversation is ValueNotifier) {
          (_conversation.conversation as ValueNotifier<List<ChatMessage>>)
                  .value =
              history;
          // Scroll to bottom after frame
          WidgetsBinding.instance.addPostFrameCallback(
            (_) => _scrollToBottom(force: true),
          );
        }
      } catch (e) {
        debugPrint("Could not hydrate session history: $e");
      }
    }

    // Show a message indicating the session is loaded
    StatusToast.show(context, 'Loaded session: ${session.displayTitle}');
  }

  void _scrollToBottom({bool force = false}) {
    if (!mounted || !_scrollController.hasClients) return;

    final position = _scrollController.position;
    final double extentAfter = position.extentAfter;
    final double maxScroll = position.maxScrollExtent;

    // 1. Check if user is actively manual scrolling
    final bool isUserScrolling = position.userScrollDirection != ScrollDirection.idle;

    // 2. Threshold to detect if we should "stick" to the bottom.
    // We use a larger threshold (300px) to ensure we don't lose stickiness
    // when large blocks of text arrive between frames.
    final bool isNearBottom = extentAfter < 300.0;

    // 3. Logic to decide whether to scroll:
    // - Always scroll if forced (e.g. user just sent a message)
    // - Scroll if we are near the bottom AND the user isn't actively manual scrolling
    // - Scroll if the list is empty/new
    if (!force && (isUserScrolling || (!isNearBottom && maxScroll > 0))) {
      return;
    }

    // Use addPostFrameCallback to ensure the layout has updated
    // with the latest message sizes before calculating the target offset.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) return;

      final currentMax = _scrollController.position.maxScrollExtent;
      final currentOffset = _scrollController.offset;

      // If we are already at the bottom (or very close), no need to start a new animation.
      if ((currentMax - currentOffset).abs() < 5.0) return;

      // Animate smoothly but quickly to the bottom.
      _scrollController.animateTo(
        currentMax,
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeOutCubic,
      );
    });
  }

  void _sendMessage() {
    if (_textController.text.trim().isEmpty) return;
    final text = _textController.text;
    _textController.clear();
    _conversation.sendRequest(UserMessage.text(text));

    // Request focus after the frame to ensure that if the layout transitioned
    // from Hero to Conversation state, the new TextField is ready to receive focus.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _focusNode.requestFocus();
      }
    });

    _scrollToBottom(force: true);
  }

  bool _isSidebarOpen = false;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 900;
        final showDrawer = isMobile;
        final showSidebar = !isMobile && _isSidebarOpen;

        return Scaffold(
          backgroundColor: AppColors.backgroundDark,
          drawer: showDrawer
              ? Drawer(
                  width: 280,
                  backgroundColor: AppColors.backgroundCard,
                  shape: const RoundedRectangleBorder(
                    borderRadius: BorderRadius.zero,
                  ),
                  child: Column(
                    children: [
                      Expanded(
                        child: ValueListenableBuilder<String?>(
                          valueListenable: _sessionService.currentSessionId,
                          builder: (context, currentSessionId, _) {
                            return SessionPanel(
                              sessionService: _sessionService,
                              onNewSession: _startNewSession,
                              onSessionSelected: (id) {
                                _loadSession(id);
                                Navigator.pop(context); // Close drawer
                              },
                              currentSessionId: currentSessionId,
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                )
              : null,
          appBar: _buildAppBar(isMobile: isMobile),
          body: Row(
            children: [
              // Sidebar for desktop
              if (showSidebar)
                SizedBox(
                  width: 280,
                  child: ValueListenableBuilder<String?>(
                    valueListenable: _sessionService.currentSessionId,
                    builder: (context, currentSessionId, _) {
                      return SessionPanel(
                        sessionService: _sessionService,
                        onNewSession: _startNewSession,
                        onSessionSelected: (id) {
                          _loadSession(id);
                        },
                        currentSessionId: currentSessionId,
                      );
                    },
                  ),
                ),
              // Divider
              if (showSidebar)
                VerticalDivider(
                  width: 1,
                  thickness: 1,
                  color: AppColors.surfaceBorder,
                ),
              // Main conversation area
              Expanded(
                child: ValueListenableBuilder<List<ChatMessage>>(
                  valueListenable: _conversation.conversation,
                  builder: (context, messages, _) {
                    if (messages.isEmpty) {
                      return _buildHeroEmptyState();
                    }
                    return Column(
                      children: [
                        Expanded(child: _buildMessageList(messages)),
                        _buildInputArea(),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  PreferredSizeWidget _buildAppBar({required bool isMobile}) {
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
      leading: Builder(
        builder: (context) {
          return IconButton(
            icon: Icon(
              isMobile
                  ? Icons.menu
                  : (_isSidebarOpen ? Icons.menu_open : Icons.menu),
              color: AppColors.textSecondary,
            ),
            onPressed: () {
              if (isMobile) {
                Scaffold.of(context).openDrawer();
              } else {
                setState(() {
                  _isSidebarOpen = !_isSidebarOpen;
                });
              }
            },
          );
        },
      ),
      titleSpacing: 0,
      title: LayoutBuilder(
        builder: (context, constraints) {
          final isCompact = constraints.maxWidth < 600;
          return Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Logo/Icon - clickable to return to home
              _buildLogoButton(),
              const SizedBox(width: 8),
              // Title
              if (!isCompact)
                InkWell(
                  onTap: _startNewSession,
                  child: Stack(
                    children: [
                      // Shadow Layer
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
                      // Gradient Layer
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
              // Project Selector (Left aligned now)
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 250),
                child: _buildProjectSelector(),
              ),
            ],
          );
        },
      ),
      actions: [
        // Status indicator
        ValueListenableBuilder<bool>(
          valueListenable: _contentGenerator.isConnected,
          builder: (context, isConnected, _) {
            return ValueListenableBuilder<bool>(
              valueListenable: _contentGenerator.isProcessing,
              builder: (context, isProcessing, _) {
                return _buildStatusIndicator(isProcessing, isConnected);
              },
            );
          },
        ),
        const SizedBox(width: 12),
        // Settings / Tool Config
        _buildSettingsButton(),
        const SizedBox(width: 8),
        // User Profile
        _buildUserProfileButton(),
        const SizedBox(width: 16),
      ],
    );
  }

  Widget _buildLogoButton({bool isMobile = false}) {
    return Tooltip(
      message: 'New Session',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: _startNewSession,
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: EdgeInsets.all(isMobile ? 6 : 8),
            child: Icon(
              Icons.smart_toy,
              color: AppColors.primaryTeal,
              size: isMobile ? 24 : 32,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSettingsButton() {
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

  Widget _buildUserProfileButton() {
    final authService = Provider.of<AuthService>(context, listen: false);
    final user = authService.currentUser;
    final photoUrl = user?.photoUrl;

    return Tooltip(
      message: user?.displayName ?? 'User Profile',
      child: Material(
        color: Colors.transparent,
        shape: const CircleBorder(),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () {
            // TODO: Show profile dialog or sign out option
            showDialog(
              context: context,
              builder: (context) => AlertDialog(
                title: Text(user?.displayName ?? 'Profile'),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(user?.email ?? ''),
                    const SizedBox(height: 20),
                    ElevatedButton(
                      onPressed: () async {
                        final navigator = Navigator.of(context);
                        await authService.signOut();
                        navigator.pop();
                      },
                      child: const Text('Sign Out'),
                    ),
                  ],
                ),
              ),
            );
          },
          child: CircleAvatar(
            backgroundColor: AppColors.primaryTeal,
            radius: 16,
            backgroundImage: photoUrl != null ? NetworkImage(photoUrl) : null,
            child: photoUrl == null
                ? Text(
                    user?.displayName?.substring(0, 1).toUpperCase() ?? 'U',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  )
                : null,
          ),
        ),
      ),
    );
  }

  Widget _buildStatusIndicator(
    bool isProcessing,
    bool isConnected, {
    bool compact = false,
  }) {
    Color statusColor;
    String statusText;

    if (isConnected) {
      statusColor = AppColors.success;
      statusText = 'Connected';
    } else {
      statusColor = AppColors.error;
      statusText = 'Offline';
    }

    // Get Agent URL if available
    final agentUrl = _contentGenerator.baseUrl;

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
        padding: EdgeInsets.symmetric(
          horizontal: compact ? 6 : 8,
          vertical: compact ? 3 : 4,
        ),
        decoration: BoxDecoration(
          color: statusColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Static Dot Only (User requested removal of spinner)
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: statusColor,
                shape: BoxShape.circle,
              ),
            ),
            if (!compact) ...[
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
          ],
        ),
      ),
    );
  }

  Widget _buildProjectSelector() {
    return ValueListenableBuilder<bool>(
      valueListenable: _projectService.isLoading,
      builder: (context, isLoading, _) {
        return ValueListenableBuilder<List<GcpProject>>(
          valueListenable: _projectService.projects,
          builder: (context, projects, _) {
            return ValueListenableBuilder<GcpProject?>(
              valueListenable: _projectService.selectedProject,
              builder: (context, selectedProject, _) {
                return ValueListenableBuilder<String?>(
                  valueListenable: _projectService.error,
                  builder: (context, error, _) {
                    return ValueListenableBuilder<List<GcpProject>>(
                      valueListenable: _projectService.recentProjects,
                      builder: (context, recentProjects, _) {
                        return _ProjectSelectorDropdown(
                          projects: projects,
                          recentProjects: recentProjects,
                          selectedProject: selectedProject,
                          isLoading: isLoading,
                          error: error,
                          onProjectSelected: (project) {
                            _projectService.selectProjectInstance(project);
                          },
                          onRefresh: () {
                            _projectService.fetchProjects();
                          },
                          onSearch: (query) {
                            _projectService.fetchProjects(query: query);
                          },
                        );
                      },
                    );
                  },
                );
              },
            );
          },
        );
      },
    );
  }

  Widget _buildMessageList(List<ChatMessage> messages) {
    return Stack(
      children: [
        // 1. Tech Grid Background
        Positioned.fill(child: CustomPaint(painter: const TechGridPainter())),
        // Gradient Overlay for Fade Effect
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                stops: const [0.5, 1.0],
                colors: [Colors.transparent, AppColors.backgroundDark],
              ),
            ),
          ),
        ),

        // 2. Centered Chat Stream
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.fromLTRB(8, 12, 8, 12),
              itemCount: messages.length + 1, // +1 for typing indicator
              itemBuilder: (context, index) {
                if (index == messages.length) {
                  // Typing indicator at the end
                  return ValueListenableBuilder<bool>(
                    valueListenable: _contentGenerator.isProcessing,
                    builder: (context, isProcessing, _) {
                      if (!isProcessing) return const SizedBox.shrink();
                      return _buildTypingIndicator();
                    },
                  );
                }
                final msg = messages[index];

                // Determine vertical spacing
                double topSpacing = 4.0;
                if (index > 0) {
                  final prevMsg = messages[index - 1];
                  final isSameSender =
                      (msg is UserMessage && prevMsg is UserMessage) ||
                      ((msg is AiTextMessage || msg is AiUiMessage) &&
                          (prevMsg is AiTextMessage || prevMsg is AiUiMessage));
                  if (!isSameSender) {
                    topSpacing = 24.0;
                  }
                } else {
                  // First message
                  topSpacing = 16.0;
                }

                return Padding(
                  padding: EdgeInsets.only(top: topSpacing),
                  child: _MessageItem(
                    message: msg,
                    host: _conversation.host,
                    animation: _typingController,
                  ),
                );
              },
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildHeroEmptyState() {
    final authService = Provider.of<AuthService>(context, listen: false);
    final user = authService.currentUser;
    // Get first name for "Hi [Name]"
    String name = 'there';
    if (user?.displayName != null && user!.displayName!.isNotEmpty) {
      name = user.displayName!.split(' ').first;
    }

    return Stack(
      children: [
        Positioned.fill(child: CustomPaint(painter: const TechGridPainter())),
        Center(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1000),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Greeting
                    ShaderMask(
                      shaderCallback: (bounds) => const LinearGradient(
                        colors: [
                          AppColors.primaryBlue,
                          AppColors.secondaryPurple,
                        ],
                      ).createShader(bounds),
                      child: Text(
                        'Hi $name',
                        style: const TextStyle(
                          fontSize: 48,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Where should we start debugging?',
                      style: TextStyle(
                        fontSize: 24,
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.w400,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 48),

                    // Hero Input Field
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 700),
                      child: _buildHeroInput(),
                    ),

                    const SizedBox(height: 32),

                    // Action Chips
                    ValueListenableBuilder<List<String>>(
                      valueListenable: _suggestedActions,
                      builder: (context, suggestions, _) {
                        if (suggestions.isEmpty) return const SizedBox.shrink();

                        return SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: suggestions.asMap().entries.map((entry) {
                              final index = entry.key;
                              final suggestion = entry.value;
                              return Padding(
                                padding: EdgeInsets.only(
                                  right: index < suggestions.length - 1
                                      ? 12
                                      : 0,
                                ),
                                child: _buildHeroActionChip(suggestion),
                              );
                            }).toList(),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildHeroInput() {
    return ValueListenableBuilder<bool>(
      valueListenable: _contentGenerator.isProcessing,
      builder: (context, isProcessing, _) {
        return UnifiedPromptInput(
          key: _inputKey,
          controller: _textController,
          focusNode: _focusNode,
          isProcessing: isProcessing,
          onSend: _sendMessage,
          onCancel: _contentGenerator.cancelRequest,
        );
      },
    );
  }

  Widget _buildHeroActionChip(String label) {
    return GlowActionChip(
      label: label,
      icon: Icons.bolt_rounded,
      onTap: () {
        _textController.text = label;
        _sendMessage();
      },
    );
  }

  Widget _buildTypingIndicator() {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment:
              CrossAxisAlignment.center, // Center aligned for dots
          children: [
            // Agent Icon
            const AgentAvatar(),
            // Typing Dots Bubble
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.secondaryPurple.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: AppColors.secondaryPurple.withValues(alpha: 0.1),
                  width: 1,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: List.generate(3, (index) {
                  return AnimatedBuilder(
                    animation: _typingController,
                    builder: (context, child) {
                      final delay = index * 0.2;
                      final animValue =
                          ((_typingController.value + delay) % 1.0 * 2.0).clamp(
                            0.0,
                            1.0,
                          );
                      final bounce =
                          (animValue < 0.5
                              ? animValue * 2
                              : 2 - animValue * 2) *
                          0.4;

                      return Container(
                        margin: EdgeInsets.only(right: index < 2 ? 4 : 0),
                        child: Transform.translate(
                          offset: Offset(0, -bounce * 4),
                          child: Container(
                            width: 6,
                            height: 6,
                            decoration: BoxDecoration(
                              color: AppColors.secondaryPurple.withValues(
                                alpha: 0.4 + bounce,
                              ),
                              shape: BoxShape.circle,
                            ),
                          ),
                        ),
                      );
                    },
                  );
                }),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      decoration: BoxDecoration(
        color: Colors
            .transparent, // Floating effect: Transparent background wrapper
      ),
      child: SafeArea(
        top: false,
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900), // Max width 900px
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Suggested Actions
                _buildSuggestedActions(),
                const SizedBox(height: 12),
                // Unified Input Container
                ValueListenableBuilder<bool>(
                  valueListenable: _contentGenerator.isProcessing,
                  builder: (context, isProcessing, child) {
                    return UnifiedPromptInput(
                      key: _inputKey,
                      controller: _textController,
                      focusNode: _focusNode,
                      isProcessing: isProcessing,
                      onSend: _sendMessage,
                      onCancel: _contentGenerator.cancelRequest,
                    );
                  },
                ),
                // Compact keyboard hint
                Align(
                  alignment: Alignment.centerLeft,
                  child: Padding(
                    padding: const EdgeInsets.only(top: 8, left: 16),
                    child: Text(
                      'Enter to send • Shift+Enter for new line',
                      style: TextStyle(
                        fontSize: 11,
                        color: AppColors.textMuted.withValues(alpha: 0.6),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSuggestedActions() {
    return ValueListenableBuilder<List<String>>(
      valueListenable: _suggestedActions,
      builder: (context, suggestions, _) {
        if (suggestions.isEmpty) return const SizedBox.shrink();

        return SizedBox(
          height: 32,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: suggestions.length,
            separatorBuilder: (context, index) => const SizedBox(width: 8),
            padding: const EdgeInsets.symmetric(
              horizontal: 4,
            ), // Align with input
            itemBuilder: (context, index) {
              final action = suggestions[index];
              return _buildActionChip(action);
            },
          ),
        );
      },
    );
  }

  Widget _buildActionChip(String text) {
    return GlowActionChip(
      label: text,
      icon: Icons.bolt_rounded,
      compact: true,
      onTap: () {
        _textController.text = text;
        _sendMessage();
      },
    );
  }

  @override
  void dispose() {
    _sessionSubscription?.cancel();
    _suggestionsSubscription?.cancel();
    _projectService.selectedProject.removeListener(_onProjectChanged);
    _typingController.dispose();
    _conversation.dispose();
    _focusNode.dispose();
    super.dispose();
  }
}

/// Standalone Agent Avatar widget for reuse
class AgentAvatar extends StatelessWidget {
  const AgentAvatar({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(right: 8),
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        color: AppColors.secondaryPurple.withValues(alpha: 0.2),
        shape: BoxShape.circle,
        border: Border.all(
          color: AppColors.secondaryPurple.withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: const Icon(
        Icons.smart_toy,
        size: 18, // UNIFIED SIZE: 18px
        color: AppColors.secondaryPurple,
      ),
    );
  }
}

/// Animated message item widget
class _MessageItem extends StatefulWidget {
  final ChatMessage message;
  final GenUiHost host;
  final AnimationController animation;

  const _MessageItem({
    required this.message,
    required this.host,
    required this.animation,
  });

  @override
  State<_MessageItem> createState() => _MessageItemState();
}

class _MessageItemState extends State<_MessageItem>
    with SingleTickerProviderStateMixin {
  late AnimationController _entryController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _entryController = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );

    _fadeAnimation = CurvedAnimation(
      parent: _entryController,
      curve: Curves.easeOut,
    );

    _slideAnimation =
        Tween<Offset>(begin: const Offset(0, 0.015), end: Offset.zero).animate(
          CurvedAnimation(parent: _entryController, curve: Curves.easeOutCubic),
        );

    _entryController.forward();
  }

  @override
  void dispose() {
    _entryController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: SlideTransition(
        position: _slideAnimation,
        child: _buildMessageContent(),
      ),
    );
  }

  Widget _buildMessageContent() {
    final msg = widget.message;

    if (msg is UserMessage) {
      final isShort = !msg.text.contains('\n') && msg.text.length < 80;
      return Align(
        alignment: Alignment.centerRight,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.end,
          crossAxisAlignment: isShort
              ? CrossAxisAlignment.center
              : CrossAxisAlignment.start,
          children: [
            // Spacer to push content
            const Spacer(),

            // Message Bubble
            Flexible(
              flex: 0,
              child: Container(
                constraints: const BoxConstraints(maxWidth: 900),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.primaryBlue.withValues(
                      alpha: 0.15,
                    ), // Blue Accent
                    borderRadius: BorderRadius.circular(12), // Modern Radius
                    border: Border.all(
                      color: AppColors.primaryBlue.withValues(alpha: 0.3),
                      width: 1,
                    ),
                  ),
                  child: SelectionArea(
                    child: MarkdownBody(
                      data: msg.text,
                      styleSheet: MarkdownStyleSheet(
                        p: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          height: 1.4,
                        ),
                        code: TextStyle(
                          backgroundColor: Colors.black.withValues(alpha: 0.2),
                          color: Colors.white,
                          fontSize: 12,
                          fontFamily: AppTheme.codeStyle.fontFamily,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8), // Gap 8px
            // User Avatar
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.primaryTeal,
              ),
              clipBehavior: Clip.antiAlias,
              child: Consumer<AuthService>(
                builder: (context, auth, _) {
                  final user = auth.currentUser;
                  if (user?.photoUrl != null) {
                    return Image.network(user!.photoUrl!, fit: BoxFit.cover);
                  }
                  return Center(
                    child: Text(
                      (user?.displayName ?? 'U').substring(0, 1).toUpperCase(),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      );
    } else if (msg is AiTextMessage) {
      final isShort = !msg.text.contains('\n') && msg.text.length < 80;
      return Align(
        alignment: Alignment.centerLeft,
        child: Row(
          crossAxisAlignment: isShort
              ? CrossAxisAlignment.center
              : CrossAxisAlignment.start,
          children: [
            // Agent Icon
            const AgentAvatar(),
            // Message Bubble
            Flexible(
              child: Container(
                constraints: const BoxConstraints(maxWidth: 900),
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B), // Dark Background for AI
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.1),
                    width: 1,
                  ),
                ),
                child: SelectionArea(
                  child: MarkdownBody(
                    data: msg.text,
                    styleSheet: MarkdownStyleSheet(
                      p: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 14,
                        height:
                            1.6, // Increased line height for better readability
                      ),
                      pPadding: const EdgeInsets.only(bottom: 12),
                      h1: const TextStyle(
                        color: AppColors.primaryTeal,
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.5,
                      ),
                      h1Padding: const EdgeInsets.only(top: 16, bottom: 8),
                      h2: const TextStyle(
                        color: AppColors.primaryCyan,
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.3,
                      ),
                      h2Padding: const EdgeInsets.only(top: 14, bottom: 6),
                      h3: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                      h3Padding: const EdgeInsets.only(top: 12, bottom: 4),
                      code: TextStyle(
                        backgroundColor: const Color(
                          0xFF0F172A,
                        ), // Dark "code pill" bg
                        color: AppColors.primaryCyan, // Cyan text
                        fontSize: 13,
                        fontFamily: AppTheme.codeStyle.fontFamily,
                        fontWeight: FontWeight.w500,
                      ),
                      codeblockDecoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.1),
                        ),
                      ),
                      blockquoteDecoration: BoxDecoration(
                        color: AppColors.primaryTeal.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(8),
                        border: Border(
                          left: BorderSide(
                            color: AppColors.primaryTeal.withValues(alpha: 0.5),
                            width: 3,
                          ),
                        ),
                      ),
                      blockquotePadding: const EdgeInsets.all(12),
                      // Premium Table Styling
                      tableHead: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                        fontSize: 12,
                      ),
                      tableBody: const TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 12,
                      ),
                      tableBorder: TableBorder.all(
                        color: Colors.white.withValues(alpha: 0.1),
                        width: 1,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      tableCellsPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                      tableCellsDecoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.02),
                      ),
                      listBullet: const TextStyle(
                        color: AppColors.primaryTeal,
                        fontWeight: FontWeight.bold,
                      ),
                      listIndent: 20,
                      listBulletPadding: const EdgeInsets.only(right: 8),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    } else if (msg is AiUiMessage) {
      return Align(
        alignment: Alignment.centerLeft,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const AgentAvatar(),
            // Message Bubble / Tool Surface
            Flexible(
              child: Container(
                constraints: const BoxConstraints(maxWidth: 950),
                // No decoration here to avoid double border - inner widgets (ToolLog) handle their own borders
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: GenUiSurface(
                    host: widget.host,
                    surfaceId: msg.surfaceId,
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    }
    return const SizedBox.shrink();
  }
}

/// Modern searchable project selector with combobox functionality
class _ProjectSelectorDropdown extends StatefulWidget {
  final List<GcpProject> projects;
  final List<GcpProject> recentProjects;
  final GcpProject? selectedProject;
  final bool isLoading;
  final String? error;
  final ValueChanged<GcpProject?> onProjectSelected;
  final VoidCallback onRefresh;
  final ValueChanged<String> onSearch;

  const _ProjectSelectorDropdown({
    required this.projects,
    required this.recentProjects,
    required this.selectedProject,
    required this.isLoading,
    this.error,
    required this.onProjectSelected,
    required this.onRefresh,
    required this.onSearch,
  });

  @override
  State<_ProjectSelectorDropdown> createState() =>
      _ProjectSelectorDropdownState();
}

class _ProjectSelectorDropdownState extends State<_ProjectSelectorDropdown>
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
      CurvedAnimation(parent: _animationController, curve: Curves.easeOutCubic),
    );
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

  // The projects list is already filtered by backend if query matches,
  // effectively we just show 'widget.projects'.
  // But for better UX during 'isLoading' or empty/cleared search, we might want local logic too?
  // Current logic: If backend returns list, that's the list.
  List<GcpProject> get _filteredProjects {
    // If we are searching and waiting, maybe keep showing old results or show loading?
    // For now, trust the state.
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
    // Focus the search field after a short delay
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
                width: 320,
                child: GestureDetector(
                  onTap: () {}, // Prevent tap from closing
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
    return StatefulBuilder(
      builder: (context, setDropdownState) {
        return Container(
          constraints: const BoxConstraints(maxHeight: 400),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
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
                // Search input as Header
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
                      hintStyle: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 13,
                      ),
                      prefixIcon: Icon(
                        Icons.search,
                        size: 18,
                        color: AppColors.textMuted,
                      ),
                      suffixIcon: _searchController.text.isNotEmpty
                          ? IconButton(
                              icon: Icon(
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

                      // Debounce search to avoid too many API calls
                      _debounceTimer?.cancel();
                      _debounceTimer =
                          Timer(const Duration(milliseconds: 500), () {
                        widget.onSearch(value);
                      });
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
                // Header with refresh button
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
                          color: AppColors.primaryTeal.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Icon(
                          Icons.cloud_outlined,
                          size: 14,
                          color: AppColors.primaryTeal,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'GCP Projects',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textMuted,
                          letterSpacing: 0.5,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        '${_filteredProjects.length} projects',
                        style: TextStyle(
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
                                ? SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(
                                        AppColors.primaryTeal,
                                      ),
                                    ),
                                  )
                                : Icon(
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
                // Custom project option when search doesn't match
                if (_searchQuery.isNotEmpty && _filteredProjects.isEmpty)
                  _buildUseCustomProjectOption(_searchQuery, setDropdownState),
                // Loading indicator for search
                if (widget.isLoading && _searchQuery.isNotEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 32),
                    child: Center(
                      child: SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            AppColors.primaryTeal,
                          ),
                        ),
                      ),
                    ),
                  ),
                // Project list
                if (_searchQuery.isEmpty && !widget.isLoading) ...[
                  if (widget.error != null)
                    Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        children: [
                          Icon(
                            Icons.error_outline,
                            size: 32,
                            color: Colors.redAccent,
                          ),
                          const SizedBox(height: 12),
                          Text(
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
                            style: TextStyle(
                              fontSize: 11,
                              color: AppColors.textMuted,
                            ),
                          ),
                        ],
                      ),
                    )
                  else if (widget.projects.isEmpty)
                    Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        children: [
                          Icon(
                            Icons.cloud_off_outlined,
                            size: 32,
                            color: AppColors.textMuted,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'No projects available',
                            style: TextStyle(
                              fontSize: 13,
                              color: AppColors.textMuted,
                            ),
                          ),
                        ],
                      ),
                    )
                  else ...[
                    // Recent Projects
                    if (widget.recentProjects.isNotEmpty) ...[
                      Padding(
                        padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
                        child: Text(
                          'RECENT',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textMuted.withValues(alpha: 0.7),
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                      ListView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        itemCount: widget.recentProjects.length,
                        itemBuilder: (context, index) {
                          final project = widget.recentProjects[index];
                          final isSelected =
                              widget.selectedProject?.projectId ==
                              project.projectId;
                          return _buildProjectItem(project, isSelected);
                        },
                      ),
                      const Divider(height: 1, color: Colors.white10),
                    ],
                    // All Projects (Limited)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
                      child: Row(
                        children: [
                          Text(
                            'ALL PROJECTS',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textMuted.withValues(alpha: 0.7),
                              letterSpacing: 0.5,
                            ),
                          ),
                          if (widget.projects.length > 10)
                            Padding(
                              padding: const EdgeInsets.only(left: 8),
                              child: Text(
                                '(Showing top 10)',
                                style: TextStyle(
                                  fontSize: 10,
                                  color: AppColors.textMuted.withValues(
                                    alpha: 0.5,
                                  ),
                                  fontStyle: FontStyle.italic,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                    Flexible(
                      child: ListView.builder(
                        shrinkWrap: true,
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        // Limit to 10 entries when not searching
                        itemCount: widget.projects.length > 10
                            ? 10
                            : widget.projects.length,
                        itemBuilder: (context, index) {
                          final project = widget.projects[index];
                          final isSelected =
                              widget.selectedProject?.projectId ==
                              project.projectId;
                          return _buildProjectItem(project, isSelected);
                        },
                      ),
                    ),
                  ],
                ] else if (_filteredProjects.isNotEmpty)
                  Flexible(
                    child: ListView.builder(
                      shrinkWrap: true,
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      itemCount: _filteredProjects.length,
                      itemBuilder: (context, index) {
                        final project = _filteredProjects[index];
                        final isSelected =
                            widget.selectedProject?.projectId ==
                            project.projectId;

                        return _buildProjectItem(project, isSelected);
                      },
                    ),
                  )
                else if (_searchQuery.isNotEmpty && _filteredProjects.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      children: [
                        Icon(
                          Icons.search_off,
                          size: 32,
                          color: AppColors.textMuted,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'No matching projects',
                          style: TextStyle(
                            fontSize: 13,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),
                // Use custom project when there's a search with some results
                if (_searchQuery.isNotEmpty && _filteredProjects.isNotEmpty)
                  _buildUseCustomProjectOption(_searchQuery, setDropdownState),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildUseCustomProjectOption(
    String projectId,
    StateSetter setDropdownState,
  ) {
    // Don't show if exact match exists
    final exactMatch = widget.projects.any((p) => p.projectId == projectId);
    if (exactMatch) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.fromLTRB(8, 4, 8, 8),
      decoration: BoxDecoration(
        color: AppColors.primaryTeal.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.primaryTeal.withValues(alpha: 0.3)),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _selectCustomProject(projectId),
          borderRadius: BorderRadius.circular(10),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: AppColors.primaryTeal.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Icon(
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
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: AppColors.primaryTeal,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        'Press Enter or click to use this project ID',
                        style: TextStyle(
                          fontSize: 11,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
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
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            widget.onProjectSelected(project);
            _closeDropdown();
          },
          borderRadius: BorderRadius.circular(10),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
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
                              AppColors.primaryTeal.withValues(alpha: 0.3),
                              AppColors.primaryCyan.withValues(alpha: 0.2),
                            ],
                          )
                        : null,
                    color: isSelected
                        ? null
                        : Colors.white.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    isSelected ? Icons.folder : Icons.folder_outlined,
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
                          style: TextStyle(
                            fontSize: 11,
                            color: AppColors.textMuted,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                ),
                if (isSelected)
                  Container(
                    padding: const EdgeInsets.all(2),
                    decoration: BoxDecoration(
                      color: AppColors.primaryTeal,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.check,
                      size: 12,
                      color: AppColors.backgroundDark,
                    ),
                  ),
              ],
            ),
          ),
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
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
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
                  color: _isOpen ? AppColors.primaryTeal : AppColors.textMuted,
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
