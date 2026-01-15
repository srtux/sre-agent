import 'dart:math' as math;
import 'dart:ui';
import 'package:flutter/material.dart';
import '../../theme/app_theme.dart';

/// Model for a reasoning step
class ReasoningStep {
  final String id;
  final String type; // 'observation', 'analysis', 'hypothesis', 'conclusion', 'action'
  final String content;
  final double confidence;
  final List<String> evidenceIds;
  final String? outcome;
  final bool isActive;

  ReasoningStep({
    required this.id,
    required this.type,
    required this.content,
    this.confidence = 0.0,
    this.evidenceIds = const [],
    this.outcome,
    this.isActive = false,
  });

  factory ReasoningStep.fromJson(Map<String, dynamic> json) {
    return ReasoningStep(
      id: json['id'] ?? '',
      type: json['type'] ?? 'observation',
      content: json['content'] ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      evidenceIds: List<String>.from(json['evidence_ids'] ?? []),
      outcome: json['outcome'],
      isActive: json['is_active'] ?? false,
    );
  }
}

/// Model for evidence/data points
class Evidence {
  final String id;
  final String source;
  final String type; // 'metric', 'log', 'trace', 'alert', 'config'
  final String summary;
  final double relevance;
  final Map<String, dynamic>? data;

  Evidence({
    required this.id,
    required this.source,
    required this.type,
    required this.summary,
    this.relevance = 0.0,
    this.data,
  });

  factory Evidence.fromJson(Map<String, dynamic> json) {
    return Evidence(
      id: json['id'] ?? '',
      source: json['source'] ?? '',
      type: json['type'] ?? 'log',
      summary: json['summary'] ?? '',
      relevance: (json['relevance'] as num?)?.toDouble() ?? 0.0,
      data: json['data'],
    );
  }
}

/// Model for the AI reasoning visualization
class AIReasoningData {
  final String agentName;
  final String currentTask;
  final List<ReasoningStep> steps;
  final List<Evidence> evidence;
  final String? conclusion;
  final double overallConfidence;
  final String status; // 'analyzing', 'reasoning', 'concluding', 'complete'

  AIReasoningData({
    required this.agentName,
    required this.currentTask,
    required this.steps,
    this.evidence = const [],
    this.conclusion,
    this.overallConfidence = 0.0,
    this.status = 'analyzing',
  });

  factory AIReasoningData.fromJson(Map<String, dynamic> json) {
    return AIReasoningData(
      agentName: json['agent_name'] ?? 'SRE Agent',
      currentTask: json['current_task'] ?? '',
      steps: (json['steps'] as List? ?? [])
          .map((s) => ReasoningStep.fromJson(Map<String, dynamic>.from(s)))
          .toList(),
      evidence: (json['evidence'] as List? ?? [])
          .map((e) => Evidence.fromJson(Map<String, dynamic>.from(e)))
          .toList(),
      conclusion: json['conclusion'],
      overallConfidence: (json['overall_confidence'] as num?)?.toDouble() ?? 0.0,
      status: json['status'] ?? 'analyzing',
    );
  }
}

/// AI Reasoning Canvas - Visualizes agent thought process
class AIReasoningCanvas extends StatefulWidget {
  final AIReasoningData data;

  const AIReasoningCanvas({super.key, required this.data});

  @override
  State<AIReasoningCanvas> createState() => _AIReasoningCanvasState();
}

class _AIReasoningCanvasState extends State<AIReasoningCanvas>
    with TickerProviderStateMixin {
  late AnimationController _entranceController;
  late AnimationController _pulseController;
  late AnimationController _thinkingController;
  late Animation<double> _entranceAnimation;
  late Animation<double> _pulseAnimation;
  late Animation<double> _thinkingAnimation;

  String? _selectedStepId;
  String? _hoveredStepId;
  bool _showEvidence = true;

  @override
  void initState() {
    super.initState();
    _entranceController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat(reverse: true);
    _thinkingController = AnimationController(
      duration: const Duration(milliseconds: 3000),
      vsync: this,
    )..repeat();

    _entranceAnimation = CurvedAnimation(
      parent: _entranceController,
      curve: Curves.easeOutCubic,
    );
    _pulseAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    _thinkingAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _thinkingController, curve: Curves.linear),
    );

    _entranceController.forward();
  }

  @override
  void dispose() {
    _entranceController.dispose();
    _pulseController.dispose();
    _thinkingController.dispose();
    super.dispose();
  }

  Color _getStepTypeColor(String type) {
    switch (type) {
      case 'observation':
        return AppColors.info;
      case 'analysis':
        return AppColors.primaryCyan;
      case 'hypothesis':
        return AppColors.warning;
      case 'conclusion':
        return AppColors.success;
      case 'action':
        return AppColors.primaryTeal;
      default:
        return AppColors.textMuted;
    }
  }

  IconData _getStepTypeIcon(String type) {
    switch (type) {
      case 'observation':
        return Icons.visibility;
      case 'analysis':
        return Icons.analytics;
      case 'hypothesis':
        return Icons.psychology;
      case 'conclusion':
        return Icons.check_circle;
      case 'action':
        return Icons.play_circle;
      default:
        return Icons.circle;
    }
  }

  Color _getEvidenceTypeColor(String type) {
    switch (type) {
      case 'metric':
        return AppColors.primaryCyan;
      case 'log':
        return AppColors.info;
      case 'trace':
        return AppColors.primaryTeal;
      case 'alert':
        return AppColors.error;
      case 'config':
        return AppColors.warning;
      default:
        return AppColors.textMuted;
    }
  }

  IconData _getEvidenceTypeIcon(String type) {
    switch (type) {
      case 'metric':
        return Icons.show_chart;
      case 'log':
        return Icons.article;
      case 'trace':
        return Icons.timeline;
      case 'alert':
        return Icons.notification_important;
      case 'config':
        return Icons.settings;
      default:
        return Icons.data_object;
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'complete':
        return AppColors.success;
      case 'concluding':
        return AppColors.primaryCyan;
      case 'reasoning':
        return AppColors.warning;
      default:
        return AppColors.info;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHeader(),
        _buildProgressBar(),
        Expanded(
          child: AnimatedBuilder(
            animation: Listenable.merge([
              _entranceAnimation,
              _pulseAnimation,
              _thinkingAnimation,
            ]),
            builder: (context, child) {
              return Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.surfaceBorder),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Stack(
                    children: [
                      // Background with neural network pattern
                      CustomPaint(
                        size: Size.infinite,
                        painter: _NeuralNetworkPainter(
                          progress: _thinkingAnimation.value,
                          entranceProgress: _entranceAnimation.value,
                        ),
                      ),
                      // Content
                      Row(
                        children: [
                          // Reasoning steps
                          Expanded(
                            flex: 3,
                            child: _buildReasoningFlow(),
                          ),
                          // Evidence panel
                          if (_showEvidence && widget.data.evidence.isNotEmpty)
                            Container(
                              width: 200,
                              decoration: BoxDecoration(
                                border: Border(
                                  left: BorderSide(
                                    color: AppColors.surfaceBorder,
                                  ),
                                ),
                              ),
                              child: _buildEvidencePanel(),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        if (widget.data.conclusion != null) _buildConclusionCard(),
      ],
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      child: Row(
        children: [
          // AI Agent icon with thinking animation
          AnimatedBuilder(
            animation: _thinkingAnimation,
            builder: (context, child) {
              return Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  gradient: SweepGradient(
                    center: Alignment.center,
                    startAngle: 0,
                    endAngle: math.pi * 2,
                    colors: [
                      AppColors.primaryTeal.withValues(alpha: 0.3),
                      AppColors.primaryCyan.withValues(alpha: 0.1),
                      AppColors.primaryBlue.withValues(alpha: 0.3),
                      AppColors.primaryTeal.withValues(alpha: 0.1),
                      AppColors.primaryTeal.withValues(alpha: 0.3),
                    ],
                    transform: GradientRotation(_thinkingAnimation.value * math.pi * 2),
                  ),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.psychology, size: 18, color: AppColors.primaryTeal),
              );
            },
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.data.agentName,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  widget.data.currentTask,
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textMuted,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          _buildStatusIndicator(),
          const SizedBox(width: 8),
          // Toggle evidence panel
          IconButton(
            onPressed: () => setState(() => _showEvidence = !_showEvidence),
            icon: Icon(
              _showEvidence ? Icons.visibility : Icons.visibility_off,
              size: 18,
            ),
            tooltip: 'Toggle evidence panel',
            style: IconButton.styleFrom(
              backgroundColor: Colors.white.withValues(alpha: 0.05),
              padding: const EdgeInsets.all(8),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusIndicator() {
    final color = _getStatusColor(widget.data.status);
    final isThinking = widget.data.status != 'complete';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isThinking)
            SizedBox(
              width: 10,
              height: 10,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: color,
              ),
            )
          else
            Icon(Icons.check, size: 12, color: color),
          const SizedBox(width: 6),
          Text(
            widget.data.status.toUpperCase(),
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressBar() {
    final completedSteps = widget.data.steps.where((s) => !s.isActive).length;
    final totalSteps = widget.data.steps.length;
    final progress = totalSteps > 0 ? completedSteps / totalSteps : 0.0;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'Confidence: ${(widget.data.overallConfidence * 100).toStringAsFixed(0)}%',
                style: const TextStyle(
                  fontSize: 10,
                  color: AppColors.textMuted,
                ),
              ),
              const Spacer(),
              Text(
                '$completedSteps / $totalSteps steps',
                style: const TextStyle(
                  fontSize: 10,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          // Progress bar with gradient
          Container(
            height: 4,
            decoration: BoxDecoration(
              color: AppColors.surfaceBorder,
              borderRadius: BorderRadius.circular(2),
            ),
            child: FractionallySizedBox(
              widthFactor: progress * _entranceAnimation.value,
              alignment: Alignment.centerLeft,
              child: Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.primaryTeal, AppColors.primaryCyan],
                  ),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildReasoningFlow() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: widget.data.steps.length,
      itemBuilder: (context, index) {
        final step = widget.data.steps[index];
        final delay = index * 0.1;
        final animProgress = ((_entranceAnimation.value - delay) / (1.0 - delay)).clamp(0.0, 1.0);

        return Opacity(
          opacity: animProgress,
          child: Transform.translate(
            offset: Offset(-20 * (1 - animProgress), 0),
            child: _buildStepCard(step, index),
          ),
        );
      },
    );
  }

  Widget _buildStepCard(ReasoningStep step, int index) {
    final isSelected = step.id == _selectedStepId;
    final isHovered = step.id == _hoveredStepId;
    final color = _getStepTypeColor(step.type);
    final isLast = index == widget.data.steps.length - 1;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Timeline indicator
        Column(
          children: [
            // Node
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: step.isActive
                    ? color.withValues(alpha: 0.3 + 0.2 * _pulseAnimation.value)
                    : color.withValues(alpha: 0.2),
                shape: BoxShape.circle,
                border: Border.all(
                  color: step.isActive ? color : color.withValues(alpha: 0.5),
                  width: step.isActive ? 2 : 1,
                ),
                boxShadow: step.isActive
                    ? [
                        BoxShadow(
                          color: color.withValues(alpha: 0.4),
                          blurRadius: 8,
                          spreadRadius: 1,
                        ),
                      ]
                    : null,
              ),
              child: Icon(
                _getStepTypeIcon(step.type),
                size: 16,
                color: color,
              ),
            ),
            // Connector line
            if (!isLast)
              Container(
                width: 2,
                height: 40,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      color.withValues(alpha: 0.5),
                      _getStepTypeColor(widget.data.steps[index + 1].type)
                          .withValues(alpha: 0.5),
                    ],
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(width: 12),
        // Step content
        Expanded(
          child: MouseRegion(
            onEnter: (_) => setState(() => _hoveredStepId = step.id),
            onExit: (_) => setState(() => _hoveredStepId = null),
            child: GestureDetector(
              onTap: () => setState(() =>
                  _selectedStepId = _selectedStepId == step.id ? null : step.id),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                margin: EdgeInsets.only(bottom: isLast ? 0 : 16),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: (isSelected || isHovered)
                      ? color.withValues(alpha: 0.15)
                      : Colors.white.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: isSelected ? color : AppColors.surfaceBorder,
                    width: isSelected ? 2 : 1,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: color.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            step.type.toUpperCase(),
                            style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.w600,
                              color: color,
                            ),
                          ),
                        ),
                        const Spacer(),
                        // Confidence indicator
                        _buildConfidenceBar(step.confidence, color),
                      ],
                    ),
                    const SizedBox(height: 8),
                    // Content
                    Text(
                      step.content,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                        height: 1.4,
                      ),
                    ),
                    // Evidence links
                    if (step.evidenceIds.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 4,
                        runSpacing: 4,
                        children: step.evidenceIds.map((id) {
                          final evidence = widget.data.evidence.firstWhere(
                            (e) => e.id == id,
                            orElse: () => Evidence(
                              id: id,
                              source: '',
                              type: 'log',
                              summary: id,
                            ),
                          );
                          return Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: _getEvidenceTypeColor(evidence.type)
                                  .withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  _getEvidenceTypeIcon(evidence.type),
                                  size: 10,
                                  color: _getEvidenceTypeColor(evidence.type),
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  evidence.source,
                                  style: TextStyle(
                                    fontSize: 9,
                                    color: _getEvidenceTypeColor(evidence.type),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ),
                    ],
                    // Outcome
                    if (step.outcome != null) ...[
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AppColors.success.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: AppColors.success.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Row(
                          children: [
                            const Icon(
                              Icons.lightbulb,
                              size: 12,
                              color: AppColors.success,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                step.outcome!,
                                style: const TextStyle(
                                  fontSize: 10,
                                  color: AppColors.success,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildConfidenceBar(double confidence, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '${(confidence * 100).toStringAsFixed(0)}%',
          style: TextStyle(
            fontSize: 9,
            color: color,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(width: 4),
        Container(
          width: 40,
          height: 4,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(2),
          ),
          child: FractionallySizedBox(
            widthFactor: confidence,
            alignment: Alignment.centerLeft,
            child: Container(
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildEvidencePanel() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.03),
            border: Border(
              bottom: BorderSide(color: AppColors.surfaceBorder),
            ),
          ),
          child: Row(
            children: [
              const Icon(Icons.inventory_2, size: 14, color: AppColors.textMuted),
              const SizedBox(width: 8),
              const Text(
                'Evidence',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const Spacer(),
              Text(
                '${widget.data.evidence.length}',
                style: const TextStyle(
                  fontSize: 11,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ),
        ),
        // Evidence list
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(8),
            itemCount: widget.data.evidence.length,
            itemBuilder: (context, index) {
              final evidence = widget.data.evidence[index];
              return _buildEvidenceItem(evidence);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildEvidenceItem(Evidence evidence) {
    final color = _getEvidenceTypeColor(evidence.type);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Icon(
                  _getEvidenceTypeIcon(evidence.type),
                  size: 12,
                  color: color,
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  evidence.source,
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                    color: AppColors.textPrimary,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            evidence.summary,
            style: const TextStyle(
              fontSize: 9,
              color: AppColors.textMuted,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          // Relevance bar
          Row(
            children: [
              Text(
                'Relevance',
                style: const TextStyle(
                  fontSize: 8,
                  color: AppColors.textMuted,
                ),
              ),
              const SizedBox(width: 4),
              Expanded(
                child: Container(
                  height: 3,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(1.5),
                  ),
                  child: FractionallySizedBox(
                    widthFactor: evidence.relevance,
                    alignment: Alignment.centerLeft,
                    child: Container(
                      decoration: BoxDecoration(
                        color: color,
                        borderRadius: BorderRadius.circular(1.5),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildConclusionCard() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.success.withValues(alpha: 0.15),
            AppColors.primaryTeal.withValues(alpha: 0.1),
          ],
        ),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.success.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppColors.success.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.lightbulb,
              size: 20,
              color: AppColors.success,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Conclusion',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: AppColors.success,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  widget.data.conclusion!,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          // Confidence badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.success.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '${(widget.data.overallConfidence * 100).toStringAsFixed(0)}%',
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppColors.success,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Neural network background painter
class _NeuralNetworkPainter extends CustomPainter {
  final double progress;
  final double entranceProgress;

  _NeuralNetworkPainter({
    required this.progress,
    required this.entranceProgress,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final random = math.Random(42);
    final nodeCount = 15;
    final nodes = <Offset>[];

    // Generate node positions
    for (int i = 0; i < nodeCount; i++) {
      nodes.add(Offset(
        random.nextDouble() * size.width,
        random.nextDouble() * size.height,
      ));
    }

    // Draw connections
    final connectionPaint = Paint()
      ..color = AppColors.primaryTeal.withValues(alpha: 0.1 * entranceProgress)
      ..strokeWidth = 0.5;

    for (int i = 0; i < nodes.length; i++) {
      for (int j = i + 1; j < nodes.length; j++) {
        final distance = (nodes[i] - nodes[j]).distance;
        if (distance < 150) {
          final alpha = (1 - distance / 150) * 0.1 * entranceProgress;
          connectionPaint.color = AppColors.primaryTeal.withValues(alpha: alpha);
          canvas.drawLine(nodes[i], nodes[j], connectionPaint);
        }
      }
    }

    // Draw nodes with animation
    for (int i = 0; i < nodes.length; i++) {
      final nodeProgress = ((progress + i / nodeCount) % 1.0);
      final pulseScale = 0.5 + 0.5 * math.sin(nodeProgress * math.pi * 2);

      final nodePaint = Paint()
        ..color = AppColors.primaryTeal.withValues(alpha: 0.2 * entranceProgress * pulseScale)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(nodes[i], 2 + 2 * pulseScale, nodePaint);
    }
  }

  @override
  bool shouldRepaint(covariant _NeuralNetworkPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.entranceProgress != entranceProgress;
  }
}
