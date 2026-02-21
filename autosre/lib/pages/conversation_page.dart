import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:genui/genui.dart';
import 'package:provider/provider.dart';

import '../agent/adk_content_generator.dart';
import '../models/time_range.dart';
import '../services/dashboard_state.dart';
import '../services/explorer_query_service.dart';
import '../services/project_service.dart';
import '../services/prompt_history_service.dart';
import '../services/session_service.dart';
import '../services/version_service.dart';
import '../theme/app_theme.dart';
import '../widgets/conversation/chat_input_area.dart';
import '../widgets/conversation/chat_message_list.dart';
import '../widgets/conversation/chat_panel_wrapper.dart';
import '../widgets/conversation/conversation_app_bar.dart';
import '../widgets/conversation/dashboard_panel_wrapper.dart';
import '../widgets/conversation/hero_empty_state.dart';
import '../widgets/conversation/project_selection_dialog.dart';
import '../widgets/conversation/investigation_rail.dart';
import '../widgets/session_panel.dart';
import '../widgets/status_toast.dart';
import 'conversation_controller.dart';

/// Re-export [AgentAvatar] so existing consumers don't break.
export '../widgets/conversation/message_item.dart' show AgentAvatar;

class ConversationPage extends StatefulWidget {
  final ADKContentGenerator? contentGenerator;
  const ConversationPage({super.key, this.contentGenerator});

  static const double kMaxContentWidth = 1000.0;

  @override
  State<ConversationPage> createState() => _ConversationPageState();
}

class _ConversationPageState extends State<ConversationPage>
    with TickerProviderStateMixin {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _focusNode = FocusNode();
  final GlobalKey _inputKey = GlobalKey(debugLabel: 'prompt_input');

  late ProjectService _projectService;
  late SessionService _sessionService;
  late PromptHistoryService _promptHistoryService;
  late DashboardState _dashboardState;
  late ConversationController _controller;
  late AnimationController _typingController;

  // Prompt History State
  List<String> _promptHistory = [];
  int _historyIndex = -1;
  String _tempInput = '';

  // Layout State
  bool _isChatOpen = true;
  bool _isChatMaximized = false;

  @override
  void initState() {
    super.initState();

    _projectService = context.read<ProjectService>();
    _sessionService = context.read<SessionService>();
    _promptHistoryService = context.read<PromptHistoryService>();
    _dashboardState = context.read<DashboardState>();

    VersionService.instance.fetch();

    // Keyboard handling (Enter to send, Up/Down for history)
    _focusNode.onKeyEvent = _handleKeyEvent;

    // Typing indicator animation — only runs while agent is processing.
    // Starting it unconditionally caused constant frame generation even when
    // the indicator was hidden, contributing to UI freezing.
    _typingController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );

    // Create the controller that manages streams and conversation lifecycle
    _controller = ConversationController(
      sessionService: _sessionService,
      dashboardState: _dashboardState,
      onScrollToBottom: _scrollToBottom,
      showToast: (message, {isError = false}) {
        if (mounted) {
          StatusToast.show(
            context,
            message,
            isError: isError,
            duration: isError
                ? const Duration(seconds: 5)
                : const Duration(seconds: 3),
          );
        }
      },
      isMounted: () => mounted,
    );

    _controller.initialize(
      widgetContentGenerator: widget.contentGenerator,
      projectId: _projectService.selectedProjectId,
    );

    // Drive typing animation from processing state changes.
    _controller.contentGenerator?.isProcessing.addListener(
      _onProcessingChanged,
    );

    _projectService.fetchProjects();
    _sessionService.fetchSessions();
    _loadPromptHistory();

    _projectService.selectedProject.addListener(_onProjectChanged);
    // Listen for project selection needed (no saved project found)
    _projectService.needsProjectSelection.addListener(_onNeedsProjectSelection);
  }

  // --------------- Keyboard & History ---------------

  KeyEventResult _handleKeyEvent(FocusNode node, KeyEvent event) {
    if (event is! KeyDownEvent) return KeyEventResult.ignored;

    if (event.logicalKey == LogicalKeyboardKey.enter) {
      if (HardwareKeyboard.instance.isShiftPressed) {
        return KeyEventResult.ignored;
      }
      _sendMessage();
      return KeyEventResult.handled;
    } else if (event.logicalKey == LogicalKeyboardKey.arrowUp) {
      if (_textController.text.isEmpty || _historyIndex != -1) {
        _navigateHistory(up: true);
        return KeyEventResult.handled;
      }
    } else if (event.logicalKey == LogicalKeyboardKey.arrowDown) {
      if (_historyIndex != -1) {
        _navigateHistory(up: false);
        return KeyEventResult.handled;
      }
    }
    return KeyEventResult.ignored;
  }

  Future<void> _loadPromptHistory() async {
    _promptHistory = await _promptHistoryService.getHistory();
  }

  void _navigateHistory({required bool up}) {
    if (_promptHistory.isEmpty) return;

    if (_historyIndex == -1) {
      if (up) {
        _tempInput = _textController.text;
        _historyIndex = _promptHistory.length - 1;
        _updateInputFromHistory();
      }
    } else {
      if (up) {
        if (_historyIndex > 0) {
          _historyIndex--;
          _updateInputFromHistory();
        }
      } else {
        if (_historyIndex < _promptHistory.length - 1) {
          _historyIndex++;
          _updateInputFromHistory();
        } else {
          _historyIndex = -1;
          _textController.text = _tempInput;
          _moveCursorToEnd();
        }
      }
    }
  }

  void _updateInputFromHistory() {
    if (_historyIndex >= 0 && _historyIndex < _promptHistory.length) {
      _textController.text = _promptHistory[_historyIndex];
      _moveCursorToEnd();
    }
  }

  void _moveCursorToEnd() {
    _textController.selection = TextSelection.fromPosition(
      TextPosition(offset: _textController.text.length),
    );
  }

  // --------------- Processing & Typing Animation ---------------

  void _onProcessingChanged() {
    final processing =
        _controller.contentGenerator?.isProcessing.value ?? false;
    if (processing) {
      if (!_typingController.isAnimating) {
        _typingController.repeat();
      }
    } else {
      _typingController.stop();
      _typingController.reset();
    }
  }

  // --------------- Actions ---------------

  void _onProjectChanged() {
    final projectId = _projectService.selectedProjectId;
    _controller.contentGenerator?.projectId = projectId;
    _controller.contentGenerator?.fetchSuggestions();

    // When a project is selected, open dashboard with logs and auto-load data
    if (projectId != null) {
      _dashboardState.batch(() {
        _dashboardState.clear();
        _dashboardState.setTimeRange(
          TimeRange.fromPreset(TimeRangePreset.fifteenMinutes),
        );
        _dashboardState.openDashboard();
        _dashboardState.setActiveTab(DashboardDataType.logs);
      });

      // Auto-load default logs for the selected project
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          final explorer = context.read<ExplorerQueryService>();
          explorer.loadDefaultLogs(projectId: projectId);
        }
      });
    }
  }

  bool _projectDialogShown = false;

  void _onNeedsProjectSelection() {
    if (!_projectService.needsProjectSelection.value) return;
    if (!mounted) return;
    if (_projectDialogShown) return;

    _projectDialogShown = true;

    // Show project selector dialog
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) => ProjectSelectionDialog(
          projectService: _projectService,
          onProjectSelected: () {
            // Project was selected, dashboard will auto-open via _onProjectChanged
          },
        ),
      ).then((_) => _projectDialogShown = false);
    });
  }

  void _sendMessage() {
    if (_textController.text.trim().isEmpty) return;
    final text = _textController.text;
    _textController.clear();

    _promptHistoryService.addPrompt(text).then((_) {
      _loadPromptHistory();
    });
    _historyIndex = -1;
    _tempInput = '';

    _controller.conversation?.sendRequest(UserMessage.text(text));

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _focusNode.requestFocus();
      }
    });

    _scrollToBottom(force: true);
  }

  void _startNewSession() {
    _controller.contentGenerator?.isProcessing.removeListener(
      _onProcessingChanged,
    );
    _controller.clearSessionState();
    if (!mounted) return;
    setState(() {
      _controller.initialize(
        widgetContentGenerator: widget.contentGenerator,
        projectId: _projectService.selectedProjectId,
      );
    });
    _controller.contentGenerator?.isProcessing.addListener(
      _onProcessingChanged,
    );
    if (mounted) {
      StatusToast.show(context, 'Starting new investigation...');
    }
  }

  Future<void> _loadSession(String sessionId) async {
    final session = await _sessionService.getSession(sessionId);
    if (session == null) {
      if (mounted) {
        StatusToast.show(context, 'Failed to load session history');
      }
      return;
    }

    _controller.contentGenerator?.isProcessing.removeListener(
      _onProcessingChanged,
    );
    _controller.contentGenerator?.sessionId = sessionId;
    _sessionService.setCurrentSession(sessionId);

    if (!mounted) return;

    setState(() {
      _controller.initialize(
        widgetContentGenerator: widget.contentGenerator,
        projectId: _projectService.selectedProjectId,
      );
    });
    _controller.contentGenerator?.isProcessing.addListener(
      _onProcessingChanged,
    );

    if (session.messages.isNotEmpty) {
      final history = <ChatMessage>[];
      for (final msg in session.messages) {
        if (msg.role == 'user' || msg.role == 'human') {
          history.add(UserMessage.text(msg.content));
        } else {
          history.add(AiTextMessage([TextPart(msg.content)]));
        }
      }

      try {
        final conv = _controller.conversation;
        if (conv != null && conv.conversation is ValueNotifier) {
          (conv.conversation as ValueNotifier<List<ChatMessage>>).value =
              history;
          WidgetsBinding.instance.addPostFrameCallback(
            (_) => _scrollToBottom(force: true),
          );
        }
      } catch (e) {
        debugPrint('Could not hydrate session history: $e');
      }
    }

    StatusToast.show(context, 'Loaded session: ${session.displayTitle}');
  }

  // --------------- Scroll ---------------

  void _scrollToBottom({bool force = false}) {
    if (!mounted || !_scrollController.hasClients) return;

    final position = _scrollController.position;
    final extentAfter = position.extentAfter;
    final maxScroll = position.maxScrollExtent;

    final isUserScrolling =
        position.userScrollDirection != ScrollDirection.idle;
    final isNearBottom = extentAfter < 300.0;

    if (!force && (isUserScrolling || (!isNearBottom && maxScroll > 0))) {
      return;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) return;

      final currentMax = _scrollController.position.maxScrollExtent;
      final currentOffset = _scrollController.offset;

      if ((currentMax - currentOffset).abs() < 5.0) return;

      _scrollController.animateTo(
        currentMax,
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeOutCubic,
      );
    });
  }

  // --------------- Build ---------------

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 900;

        return Scaffold(
          backgroundColor: AppColors.backgroundDark,
          endDrawer: _buildSessionDrawer(),
          appBar: ConversationAppBar(
            isMobile: isMobile,
            contentGenerator: _controller.contentGenerator,
            projectService: _projectService,
            sessionService: _sessionService,
            currentTraceUrl: _controller.currentTraceUrl,
            currentTraceId: _controller.currentTraceId,
            onStartNewSession: _startNewSession,
            onLoadSession: _loadSession,
            isChatOpen: _isChatOpen,
            onToggleChat: () {
              setState(() => _isChatOpen = true);
            },
          ),
          body: Row(
            children: [
              // 1. Investigation Rail
              InvestigationRail(state: _dashboardState),

              // 2. Main Workspace (Reverted to stable Row for verification)
              Expanded(
                child: Row(
                  children: [
                    if (!isMobile && (!_isChatMaximized || !_isChatOpen))
                      DashboardPanelWrapper(
                        dashboardState: _dashboardState,
                        totalWidth: constraints.maxWidth,
                        isChatOpen: _isChatOpen,
                        onPromptRequest: (prompt) {
                          _textController.text = prompt;
                          if (!_isChatOpen) setState(() => _isChatOpen = true);
                          _sendMessage();
                        },
                      ),
                    if (_isChatOpen)
                      Expanded(
                        child: ChatPanelWrapper(
                          isMaximized: _isChatMaximized,
                          onToggleMaximize: () {
                            setState(() {
                              _isChatMaximized = !_isChatMaximized;
                            });
                          },
                          onClose: () {
                            setState(() {
                              _isChatOpen = false;
                              _isChatMaximized = false;
                            });
                          },
                          onStartNewSession: _startNewSession,
                          child: ValueListenableBuilder<List<ChatMessage>>(
                            valueListenable:
                                _controller.conversation?.conversation ??
                                ValueNotifier([]),
                            builder: (context, messages, _) {
                              return ValueListenableBuilder<bool>(
                                valueListenable:
                                    _controller
                                        .contentGenerator
                                        ?.isProcessing ??
                                    ValueNotifier(false),
                                builder: (context, isProcessing, _) {
                                  if (messages.isEmpty) {
                                    return HeroEmptyState(
                                      isProcessing: isProcessing,
                                      inputKey: _inputKey,
                                      textController: _textController,
                                      focusNode: _focusNode,
                                      onSend: _sendMessage,
                                      onCancel: () => _controller
                                          .contentGenerator
                                          ?.cancelRequest(),
                                      suggestedActions:
                                          _controller.suggestedActions,
                                    );
                                  }
                                  return Column(
                                    children: [
                                      Expanded(
                                        child: ChatMessageList(
                                          messages: messages,
                                          isProcessing: isProcessing,
                                          scrollController: _scrollController,
                                          conversation:
                                              _controller.conversation!,
                                          typingAnimation: _typingController,
                                          toolCallState:
                                              _controller.toolCallState,
                                        ),
                                      ),
                                      ChatInputArea(
                                        isProcessing: isProcessing,
                                        inputKey: _inputKey,
                                        textController: _textController,
                                        focusNode: _focusNode,
                                        onSend: _sendMessage,
                                        onCancel: () => _controller
                                            .contentGenerator
                                            ?.cancelRequest(),
                                        suggestedActions:
                                            _controller.suggestedActions,
                                      ),
                                    ],
                                  );
                                },
                              );
                            },
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSessionDrawer() {
    return Drawer(
      width: 280,
      backgroundColor: AppColors.backgroundCard,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero),
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
                    Navigator.pop(context);
                  },
                  currentSessionId: currentSessionId,
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.contentGenerator?.isProcessing.removeListener(
      _onProcessingChanged,
    );
    _controller.dispose();
    // Note: _dashboardState is managed by Provider — do NOT dispose here.
    _projectService.needsProjectSelection.removeListener(
      _onNeedsProjectSelection,
    );
    _projectService.selectedProject.removeListener(_onProjectChanged);
    _typingController.dispose();
    _textController.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }
}
