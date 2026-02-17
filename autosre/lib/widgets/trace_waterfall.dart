import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
import 'package:graphview/GraphView.dart';
import 'package:vector_math/vector_math_64.dart' hide Colors;
import 'package:provider/provider.dart';
import '../models/adk_schema.dart';
import '../services/explorer_query_service.dart';
import '../theme/app_theme.dart';
import '../theme/chart_theme.dart';

class _SpanBarData {
  final String spanName;
  final double startOffsetMs;
  final double endOffsetMs;
  final String serviceName;
  final String status;
  final bool isCriticalPath;
  final SpanInfo span;
  final int depth;
  final bool hasChildren;

  _SpanBarData({
    required this.spanName,
    required this.startOffsetMs,
    required this.endOffsetMs,
    required this.serviceName,
    required this.status,
    required this.isCriticalPath,
    required this.span,
    required this.depth,
    required this.hasChildren,
  });

  double get durationMs => endOffsetMs - startOffsetMs;
  bool get isError => status == 'ERROR';
}

/// Represents the visual layout mode of the trace.
/// [timeline] displays a traditional cascading waterfall tree structure.
/// [graph] displays a nodes-and-edges architectural view.
enum TraceViewMode { timeline, graph }

/// An interactive visualization of a distributed trace, representing the lifecycle
/// of a request across multiple services.
/// It provides a toggleable view between a Timeline Waterfall and an interactive Graph,
/// alongside a rich span detail panel for inspecting attributes, correlated logs, and OpenTelemetry semantics.
class TraceWaterfall extends StatefulWidget {
  final Trace trace;

  const TraceWaterfall({super.key, required this.trace});

  @override
  State<TraceWaterfall> createState() => _TraceWaterfallState();
}

class _TraceWaterfallState extends State<TraceWaterfall> {
  late List<_SpanBarData> _spanBars;
  late Map<String, Color> _serviceColors;
  late double _totalDurationMs;
  int _errorCount = 0;
  SpanInfo? _selectedSpan;
  Set<String> _collapsedSpanIds = {};
  TraceViewMode _viewMode = TraceViewMode.timeline;

  // Optimized Lookups
  Map<String, SpanInfo> _spanMap = {};
  Map<String, List<SpanInfo>> _childrenMap = {};
  final Map<String, List<SpanInfo>> _importantChildrenMemo = {};

  // Graph Viewer Controls
  final Set<String> _expandedGraphNodes = {};
  final TransformationController _graphTransformationController =
      TransformationController();

  @override
  void initState() {
    super.initState();
    _buildSpanData();
  }

  @override
  void didUpdateWidget(covariant TraceWaterfall oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.trace.traceId != widget.trace.traceId) {
      _collapsedSpanIds.clear();
      _expandedGraphNodes.clear();
      _graphTransformationController.value = Matrix4.identity();
      _buildSpanData();
      _selectedSpan = null;
    }
  }

  Graph? _cachedGraph;
  SugiyamaAlgorithm? _cachedAlgorithm;

  void _buildSpanData() {
    _cachedGraph = null;
    _cachedAlgorithm = null;
    if (widget.trace.spans.isEmpty) {
      _spanBars = [];
      _serviceColors = {};
      _totalDurationMs = 0;
      _spanMap = {};
      _childrenMap = {};
      _importantChildrenMemo.clear();
      return;
    }

    // Initialize mapping for O(1) lookups
    _spanMap = {for (var s in widget.trace.spans) s.spanId: s};
    _importantChildrenMemo.clear();

    final sortedSpans = List<SpanInfo>.from(widget.trace.spans)
      ..sort((a, b) => a.startTime.compareTo(b.startTime));

    final traceStart = sortedSpans.first.startTime;
    final traceEnd = sortedSpans
        .map((s) => s.endTime)
        .reduce((a, b) => a.isAfter(b) ? a : b);
    _totalDurationMs = traceEnd.difference(traceStart).inMicroseconds / 1000.0;
    if (_totalDurationMs <= 0) _totalDurationMs = 1;

    // Root-relative mapping
    _childrenMap = {};
    for (final span in sortedSpans) {
      if (span.parentSpanId != null) {
        _childrenMap.putIfAbsent(span.parentSpanId!, () => []).add(span);
      }
    }

    final rootSpans = sortedSpans
        .where(
          (s) => s.parentSpanId == null || !_spanMap.containsKey(s.parentSpanId),
        )
        .toList();

    rootSpans.sort((a, b) => a.startTime.compareTo(b.startTime));

    final criticalPathIds = _findCriticalPath(rootSpans, _childrenMap);

    _errorCount = 0;
    for (final s in widget.trace.spans) {
      if (s.status == 'ERROR') _errorCount++;
    }

    final flatData = <_SpanBarData>[];
    _serviceColors = {};
    var colorIndex = 0;

    void flatten(SpanInfo span, int depth) {
      final children = _childrenMap[span.spanId] ?? [];
      final hasChildren = children.isNotEmpty;

      final service = _extractServiceName(span.name);
      if (!_serviceColors.containsKey(service)) {
        _serviceColors[service] = ChartTheme
            .seriesColors[colorIndex % ChartTheme.seriesColors.length];
        colorIndex++;
      }

      final offsetMs =
          span.startTime.difference(traceStart).inMicroseconds / 1000.0;
      final endMs = span.endTime.difference(traceStart).inMicroseconds / 1000.0;

      flatData.add(
        _SpanBarData(
          spanName: span.name,
          startOffsetMs: offsetMs,
          endOffsetMs: math.max(endMs, offsetMs + 0.1),
          serviceName: service,
          status: span.status,
          isCriticalPath: criticalPathIds.contains(span.spanId),
          span: span,
          depth: depth,
          hasChildren: hasChildren,
        ),
      );

      if (!_collapsedSpanIds.contains(span.spanId)) {
        children.sort((a, b) => a.startTime.compareTo(b.startTime));
        for (final child in children) {
          flatten(child, depth + 1);
        }
      }
    }

    for (final root in rootSpans) {
      flatten(root, 0);
    }

    _spanBars = flatData;
  }

  Set<String> _findCriticalPath(
    List<SpanInfo> roots,
    Map<String, List<SpanInfo>> childrenMap,
  ) {
    if (roots.isEmpty) return {};

    // Memoized longest path search (O(N))
    final memo = <String, (int, List<String>)>{};
    final visited = <String>{}; // For cycle detection

    (int, List<String>) findMax(SpanInfo span) {
      if (memo.containsKey(span.spanId)) return memo[span.spanId]!;

      // Cycle detection
      if (visited.contains(span.spanId)) {
        return (span.duration.inMicroseconds, [span.spanId]);
      }
      visited.add(span.spanId);

      var maxChildDuration = 0;
      var maxChildPath = <String>[];

      final children = childrenMap[span.spanId] ?? [];
      for (final child in children) {
        final res = findMax(child);
        if (res.$1 > maxChildDuration) {
          maxChildDuration = res.$1;
          maxChildPath = res.$2;
        }
      }

      final result = (
        span.duration.inMicroseconds + maxChildDuration,
        [span.spanId, ...maxChildPath],
      );
      memo[span.spanId] = result;
      return result;
    }

    var overallMax = -1;
    var overallPath = <String>[];

    for (final root in roots) {
      final res = findMax(root);
      if (res.$1 > overallMax) {
        overallMax = res.$1;
        overallPath = res.$2;
      }
    }

    return overallPath.toSet();
  }

  String _extractServiceName(String spanName) {
    final colonIndex = spanName.indexOf(':');
    final slashIndex = spanName.indexOf('/');
    final dotIndex = spanName.indexOf('.');

    var splitIndex = spanName.length;
    if (colonIndex > 0) splitIndex = math.min(splitIndex, colonIndex);
    if (slashIndex > 0) splitIndex = math.min(splitIndex, slashIndex);
    if (dotIndex > 0) splitIndex = math.min(splitIndex, dotIndex);

    return spanName.substring(0, splitIndex);
  }

  void _toggleCollapse(String spanId) {
    _cachedGraph = null;
    _cachedAlgorithm = null;
    setState(() {
      if (_collapsedSpanIds.contains(spanId)) {
        _collapsedSpanIds.remove(spanId);
      } else {
        _collapsedSpanIds.add(spanId);
      }
      _buildSpanData();
    });
  }

  @override
  Widget build(BuildContext context) {
    if (widget.trace.spans.isEmpty) {
      return _buildEmptyState();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHeader(_errorCount),
        const SizedBox(height: 8),
        _buildServiceLegend(),
        const SizedBox(height: 8),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: _selectedSpan != null ? 1 : 1,
                  child: _viewMode == TraceViewMode.timeline
                      ? _buildTreeTable()
                      : _buildGraphView(),
                ),
                if (_selectedSpan != null) ...[
                  const SizedBox(width: 16),
                  Expanded(
                    flex: 1,
                    child: _SpanDetailPanel(
                      span: _selectedSpan!,
                      traceId: widget.trace.traceId,
                      serviceColor: _serviceColors[_extractServiceName(_selectedSpan!.name)] ?? AppColors.primaryTeal,
                      onClose: () => setState(() => _selectedSpan = null),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.textMuted.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.timeline_outlined,
              size: 40,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'No spans in trace',
            style: TextStyle(color: AppColors.textMuted, fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(int errorCount) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.primaryTeal.withValues(alpha: 0.2),
                  AppColors.primaryCyan.withValues(alpha: 0.15),
                ],
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.account_tree,
              size: 18,
              color: AppColors.primaryTeal,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      'Trace Waterfall',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.primaryTeal.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        '${widget.trace.spans.length} spans',
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.primaryTeal,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    const Icon(
                      Icons.fingerprint,
                      size: 10,
                      color: AppColors.textMuted,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        widget.trace.traceId,
                        style: const TextStyle(
                          fontSize: 10,
                          fontFamily: 'monospace',
                          color: AppColors.textMuted,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Expanded(
            child: Align(
              alignment: Alignment.centerRight,
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _buildStatChip(
                      '${_totalDurationMs.toStringAsFixed(1)}ms',
                      Icons.timer_outlined,
                      AppColors.primaryCyan,
                    ),
                    if (errorCount > 0) ...[
                      const SizedBox(width: 8),
                      _buildStatChip(
                        '$errorCount errors',
                        Icons.error_outline,
                        AppColors.error,
                      ),
                    ],
                    const SizedBox(width: 8),
                    IconButton(
                      icon: const Icon(Icons.unfold_more, size: 16),
                      tooltip: 'Expand All',
                      onPressed: () {
                        setState(() {
                          _collapsedSpanIds.clear();
                          _buildSpanData();
                        });
                      },
                      color: AppColors.textSecondary,
                    ),
                    IconButton(
                      icon: const Icon(Icons.unfold_less, size: 16),
                      tooltip: 'Collapse All',
                      onPressed: () {
                        setState(() {
                          _collapsedSpanIds = widget.trace.spans
                              .map((s) => s.spanId)
                              .toSet();
                          _buildSpanData();
                        });
                      },
                      color: AppColors.textSecondary,
                    ),
                    const SizedBox(width: 8),
                    _layoutToggle(),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _layoutToggle() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _toggleButton(
            'Timeline',
            _viewMode == TraceViewMode.timeline,
            () => setState(() => _viewMode = TraceViewMode.timeline),
          ),
          _toggleButton(
            'Graph',
            _viewMode == TraceViewMode.graph,
            () => setState(() => _viewMode = TraceViewMode.graph),
          ),
        ],
      ),
    );
  }

  Widget _toggleButton(String label, bool active, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: active
              ? AppColors.primaryTeal.withValues(alpha: 0.3)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active ? Colors.white : Colors.white38,
            fontSize: 11,
          ),
        ),
      ),
    );
  }

  Widget _buildStatChip(String text, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            text,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildServiceLegend() {
    return Container(
      height: 28,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: _serviceColors.entries.map((e) {
          return Container(
            margin: const EdgeInsets.only(right: 12),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: e.value.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: e.value.withValues(alpha: 0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: e.value,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  e.key,
                  style: TextStyle(
                    fontSize: 10,
                    color: e.value,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildTreeTable() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final tableWidth = math.max(
            constraints.maxWidth,
            1000.0,
          ); // Minimum width to ensure horizontal scroll

          return SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: SizedBox(
              width: tableWidth,
              child: Column(
                children: [
                  _buildTableHeader(),
                  const Divider(height: 1, color: AppColors.surfaceBorder),
                  Expanded(
                    child: ListView.builder(
                      itemCount: _spanBars.length,
                      itemBuilder: (context, index) {
                        return _buildTableRow(_spanBars[index]);
                      },
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  bool _isImportantSpan(SpanInfo span) {
    if (span.status == 'ERROR') return true;
    final lowerName = span.name.toLowerCase();

    // Core agent ops
    if (lowerName.contains('invoke_agent') ||
        lowerName.contains('generate_content') ||
        lowerName.contains('tool') ||
        lowerName.contains('llm') ||
        lowerName.contains('chain')) {
      return true;
    }

    // Core server roots
    if (span.parentSpanId == null || span.name.startsWith('POST')) return true;

    return false;
  }

  List<SpanInfo> _getImportantChildren(
      String parentId, Map<String, List<SpanInfo>> childrenMap) {
    if (_importantChildrenMemo.containsKey(parentId)) {
      return _importantChildrenMemo[parentId]!;
    }

    final important = <SpanInfo>[];
    final children = childrenMap[parentId] ?? [];

    for (final childSpan in children) {
      if (_isImportantSpan(childSpan)) {
        important.add(childSpan);
      } else {
        // Recurse downstream
        important.addAll(_getImportantChildren(childSpan.spanId, childrenMap));
      }
    }

    _importantChildrenMemo[parentId] = important;
    return important;
  }

  Widget _buildGraphView() {
    if (_cachedGraph == null || _cachedAlgorithm == null) {
      // Generate filtered data structure for progressive disclosure
      final graph = Graph()..isTree = true;
      final nodeMap = <String, Node>{};

      // Generate node map (Safeguard: Limit graph size to 150 nodes to prevent UI freeze)
      const maxNodes = 150;
      var nodeCount = 0;

      for (final span in widget.trace.spans) {
        if (_isImportantSpan(span) || span.parentSpanId == null) {
          final node = Node.Id(span.spanId);
          nodeMap[span.spanId] = node;
          graph.addNode(node);
          nodeCount++;
          if (nodeCount >= maxNodes) break;
        }
      }

      // Initialize root in expanded map if empty
      if (_expandedGraphNodes.isEmpty && widget.trace.spans.isNotEmpty) {
        final root = widget.trace.spans.firstWhere((s) => s.parentSpanId == null,
            orElse: () => widget.trace.spans.first);
        _expandedGraphNodes.add(root.spanId);
      }

      // Build hierarchical condensed edges
      for (final parentSpanId in _expandedGraphNodes) {
        if (!nodeMap.containsKey(parentSpanId)) continue;

        final parentNode = nodeMap[parentSpanId]!;
        final importantChildren =
            _getImportantChildren(parentSpanId, _childrenMap);

        for (final child in importantChildren) {
          if (nodeMap.containsKey(child.spanId)) {
            final childNode = nodeMap[child.spanId]!;
            graph.addEdge(parentNode, childNode,
                paint: Paint()
                  ..color = AppColors.surfaceBorder
                  ..strokeWidth = 2
                  ..style = PaintingStyle.stroke);
          }
        }
      }

      final sugiyamaConfig = SugiyamaConfiguration()
        ..bendPointShape = CurvedBendPointShape(curveLength: 20)
        ..nodeSeparation = 30
        ..levelSeparation = 50
        ..orientation = SugiyamaConfiguration.ORIENTATION_LEFT_RIGHT;

      _cachedAlgorithm = SugiyamaAlgorithm(sugiyamaConfig);
      _cachedGraph = graph;
    }

    final graph = _cachedGraph!;
    final algorithm = _cachedAlgorithm!;

    return Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      clipBehavior: Clip.hardEdge,
      child: Listener(
        onPointerSignal: (pointerSignal) {
          if (pointerSignal is! PointerScrollEvent) return;

          final scaleAdjustment = pointerSignal.scrollDelta.dy > 0 ? 0.9 : 1.1;
          final newMatrix = _graphTransformationController.value.clone();
          final localPosition = pointerSignal.localPosition;

          // Scale around the mouse position relative to the viewing window
          newMatrix.translateByVector3(Vector3(localPosition.dx, localPosition.dy, 0.0));
          newMatrix.scaleByVector3(Vector3(scaleAdjustment, scaleAdjustment, 1.0));
          newMatrix.translateByVector3(Vector3(-localPosition.dx, -localPosition.dy, 0.0));

          // Constrain zoom scales between 10% and 400%
          final scale = newMatrix.getMaxScaleOnAxis();
          if (scale > 0.1 && scale < 4.0) {
            _graphTransformationController.value = newMatrix;
          }
        },
        child: InteractiveViewer(
          transformationController: _graphTransformationController,
          constrained: false,
          boundaryMargin: const EdgeInsets.all(500),
          minScale: 0.1,
          maxScale: 4.0,
          child: GraphView(
            graph: graph,
            algorithm: algorithm,
            paint: Paint()
              ..color = AppColors.surfaceBorder
              ..strokeWidth = 1
              ..style = PaintingStyle.stroke,
            builder: (Node node) {
              final spanId = node.key!.value as String;
              final spanInfo = widget.trace.spans.firstWhere((s) => s.spanId == spanId);
              return _buildGraphNode(spanInfo);
            },
          ),
        ),
      ),
    );
  }

  Widget _buildGraphNode(SpanInfo span) {
    final serviceName = _extractServiceName(span.name);
    final isSelected = _selectedSpan?.spanId == span.spanId;
    final color = span.status == 'ERROR' ? AppColors.error : (_serviceColors[serviceName] ?? AppColors.primaryTeal);

    final importantChildren = _getImportantChildren(span.spanId, _childrenMap);
    final isExpanded = _expandedGraphNodes.contains(span.spanId);

    return GestureDetector(
      onTap: () => setState(() => _selectedSpan = isSelected ? null : span),
      child: Container(
        constraints: const BoxConstraints(maxWidth: 300),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? color : color.withValues(alpha: 0.4),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  span.status == 'ERROR' ? Icons.error : Icons.check_circle,
                  color: color,
                  size: 14,
                ),
                const SizedBox(width: 4),
                Text(
                  serviceName,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              span.name,
              style: TextStyle(
                color: span.status == 'ERROR' ? AppColors.error : AppColors.textPrimary,
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
            ),
            if (span.duration.inMilliseconds >= 0)
              Text(
                '${span.duration.inMilliseconds}ms',
                style: const TextStyle(color: AppColors.textMuted, fontSize: 9),
              ),
            if (importantChildren.isNotEmpty) ...[
              const SizedBox(height: 8),
              InkWell(
                onTap: () {
                  setState(() {
                    if (isExpanded) {
                      _expandedGraphNodes.remove(span.spanId);
                      _cachedGraph = null;
                      _cachedAlgorithm = null;
                    } else {
                      _expandedGraphNodes.add(span.spanId);
                      _cachedGraph = null;
                      _cachedAlgorithm = null;
                    }
                  });
                },
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        isExpanded ? Icons.remove : Icons.add,
                        size: 10,
                        color: AppColors.textSecondary,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        isExpanded ? 'Collapse' : '${importantChildren.length} calls',
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTableHeader() {
    final showWaterfall = _selectedSpan == null;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
      decoration: const BoxDecoration(
        color: AppColors.backgroundElevated,
        borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
      ),
      child: Row(
        children: [
          Expanded(
            flex: showWaterfall ? 3 : 2,
            child: const Text(
              'Name',
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const Expanded(
            flex: 1,
            child: Text(
              'Service',
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          if (showWaterfall)
            Expanded(
              flex: 5,
              child: LayoutBuilder(
                builder: (context, constraints) {
                  return Stack(
                    children: [
                      SizedBox(height: 14, width: constraints.maxWidth),
                      const Positioned(
                        left: 0,
                        child: Text(
                          '0s',
                          style: TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 10,
                          ),
                        ),
                      ),
                      Positioned(
                        right: 0,
                        child: Text(
                          '${_totalDurationMs.toStringAsFixed(1)}ms',
                          style: const TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 10,
                          ),
                        ),
                      ),
                      Positioned(
                        left: constraints.maxWidth * 0.25,
                        child: Text(
                          '${(_totalDurationMs * 0.25).toStringAsFixed(0)}ms',
                          style: const TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 10,
                          ),
                        ),
                      ),
                      Positioned(
                        left: constraints.maxWidth * 0.5,
                        child: Text(
                          '${(_totalDurationMs * 0.5).toStringAsFixed(0)}ms',
                          style: const TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 10,
                          ),
                        ),
                      ),
                      Positioned(
                        left: constraints.maxWidth * 0.75,
                        child: Text(
                          '${(_totalDurationMs * 0.75).toStringAsFixed(0)}ms',
                          style: const TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 10,
                          ),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildTableRow(_SpanBarData bar) {
    final isSelected = _selectedSpan?.spanId == bar.span.spanId;
    final isCollapsed = _collapsedSpanIds.contains(bar.span.spanId);
    final rowBg = isSelected
        ? AppColors.primaryTeal.withValues(alpha: 0.1)
        : Colors.transparent;
    final showWaterfall = _selectedSpan == null;

    return InkWell(
      onTap: () => setState(() {
        _selectedSpan = isSelected ? null : bar.span;
      }),
      child: Container(
        color: rowBg,
        padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 8),
        constraints: const BoxConstraints(minHeight: 28),
        child: Row(
          children: [
            Expanded(
              flex: showWaterfall ? 3 : 2,
              child: Padding(
                padding: EdgeInsets.only(left: bar.depth * 16.0),
                child: Row(
                  children: [
                    if (bar.hasChildren)
                      InkWell(
                        onTap: () => _toggleCollapse(bar.span.spanId),
                        child: Icon(
                          isCollapsed
                              ? Icons.arrow_right
                              : Icons.arrow_drop_down,
                          size: 20,
                          color: AppColors.textMuted,
                        ),
                      )
                    else
                      const SizedBox(width: 20),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        bar.spanName,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 12,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Expanded(
              flex: 1,
              child: Text(
                bar.serviceName,
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 11,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (showWaterfall)
              Expanded(
                flex: 5,
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final width = constraints.maxWidth;
                    final left = (bar.startOffsetMs / _totalDurationMs) * width;
                    final barWidth = (bar.durationMs / _totalDurationMs) * width;

                    final safeWidth = math.max(barWidth, 3.0);
                    final safeLeft = left.clamp(0.0, width);

                    final barColor = bar.isError
                        ? AppColors.error
                        : (_serviceColors[bar.serviceName] ??
                              AppColors.primaryTeal);

                    return SizedBox(
                      height: 18,
                      child: Stack(
                        clipBehavior: Clip.none,
                        children: [
                          Container(
                            margin: const EdgeInsets.only(top: 8),
                            width: width,
                            height: 1,
                            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
                          ),
                          Positioned(
                            left: safeLeft,
                            width: safeWidth,
                            top: 2,
                            bottom: 2,
                            child: Tooltip(
                              message:
                                  '${bar.spanName}\nService: ${bar.serviceName}\nDuration: ${bar.durationMs.toStringAsFixed(2)}ms\nStatus: ${bar.status}',
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: AppColors.backgroundCard,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: AppColors.surfaceBorder,
                                ),
                              ),
                              textStyle: const TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 11,
                              ),
                              child: Container(
                                decoration: BoxDecoration(
                                  color: barColor.withValues(alpha: 0.7),
                                  border: Border.all(color: barColor, width: 1),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                              ),
                            ),
                          ),
                          if (safeLeft + safeWidth + 40 < width)
                            Positioned(
                              left: safeLeft + safeWidth + 4,
                              top: 2,
                              child: Tooltip(
                                message: '${bar.durationMs.toStringAsFixed(2)}ms',
                                child: Text(
                                  '${bar.durationMs.toStringAsFixed(2)}ms',
                                  style: const TextStyle(
                                    color: AppColors.textMuted,
                                    fontSize: 9,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.visible,
                                ),
                              ),
                            ),
                        ],
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

}

/// A side-panel that displays detailed metrics for a single span within a trace.
/// Features a tabbed interface for:
/// - Overview: basic execution stats
/// - Attributes: raw trace attributes (e.g. from OpenTelemetry)
/// - Logs & Events: correlated logs fetched cleanly by `traceId` and `spanId`.
/// If semantic conventions like [gen_ai.*] or [http.*] are present, it also renders
/// a persistent right-aligned pane exposing those neatly formulated details.
class _SpanDetailPanel extends StatefulWidget {
  final SpanInfo span;
  final String traceId;
  final Color serviceColor;
  final VoidCallback onClose;

  const _SpanDetailPanel({
    required this.span,
    required this.traceId,
    required this.serviceColor,
    required this.onClose,
  });

  @override
  State<_SpanDetailPanel> createState() => _SpanDetailPanelState();
}

class _SpanDetailPanelState extends State<_SpanDetailPanel> {
  List<LogEntry>? _logs;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _fetchLogs();
  }

  @override
  void didUpdateWidget(covariant _SpanDetailPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.span.spanId != widget.span.spanId) {
      _fetchLogs();
    }
  }

  Future<void> _fetchLogs() async {
    setState(() {
      _isLoading = true;
      _logs = null;
    });
    try {
      final queryService = context.read<ExplorerQueryService>();
      final logs = await queryService.fetchLogsForSpan(
        traceId: widget.traceId,
        spanId: widget.span.spanId,
      );
      if (mounted) {
        setState(() {
          _logs = logs;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _logs = [];
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundElevated,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.surfaceBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
          BoxShadow(
            color: (widget.span.status == 'ERROR' ? AppColors.error : widget.serviceColor)
                .withValues(alpha: 0.15),
            blurRadius: 24,
            spreadRadius: -4,
          ),
        ],
      ),
      child: DefaultTabController(
        length: 3,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildHeader(),
            const TabBar(
              tabs: [
                Tab(text: 'Overview'),
                Tab(text: 'Attributes'),
                Tab(text: 'Logs & Events'),
              ],
              labelColor: AppColors.primaryTeal,
              unselectedLabelColor: AppColors.textMuted,
              indicatorColor: AppColors.primaryTeal,
              dividerColor: AppColors.surfaceBorder,
              labelStyle: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
              unselectedLabelStyle: TextStyle(fontSize: 12),
              tabAlignment: TabAlignment.start,
              isScrollable: true,
            ),
            Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 3,
                  child: TabBarView(
                    children: [
                      _buildOverviewTab(),
                      _buildAttributesTab(),
                      _buildLogsTab(),
                    ],
                  ),
                ),
                if (_hasSemanticAttributes())
                  Expanded(
                    flex: 2,
                    child: Container(
                      decoration: const BoxDecoration(
                        border: Border(left: BorderSide(color: AppColors.surfaceBorder)),
                      ),
                      child: _buildSemanticAttributesPane(),
                    ),
                  ),
              ],
            ),
          ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: widget.serviceColor.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Icon(
              widget.span.status == 'ERROR' ? Icons.error : Icons.check_circle,
              size: 16,
              color: widget.span.status == 'ERROR'
                  ? AppColors.error
                  : widget.serviceColor,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.span.name,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  'Span ID: ${widget.span.spanId}',
                  style: const TextStyle(fontSize: 10, color: AppColors.textMuted, fontFamily: 'monospace'),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close, size: 16),
            onPressed: widget.onClose,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            color: AppColors.textMuted,
          ),
        ],
      ),
    );
  }

  Widget _buildOverviewTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(14),
      child: Wrap(
        spacing: 12,
        runSpacing: 8,
        children: [
          _buildDetailChip(
            'Duration',
            '${widget.span.duration.inMilliseconds}ms',
            AppColors.primaryCyan,
          ),
          _buildDetailChip(
            'Status',
            widget.span.status,
            widget.span.status == 'ERROR' ? AppColors.error : AppColors.success,
          ),
          if (widget.span.parentSpanId != null)
            _buildDetailChip(
              'Parent ID',
              widget.span.parentSpanId!,
              AppColors.textMuted,
            ),
        ],
      ),
    );
  }

  Widget _buildAttributesTab() {
    if (widget.span.attributes.isEmpty) {
      return const Center(
        child: Text('No attributes', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
      );
    }

    final sortedKeys = widget.span.attributes.keys.toList()..sort();

    return ListView.builder(
      padding: const EdgeInsets.all(14),
      itemCount: sortedKeys.length,
      itemBuilder: (context, index) {
        final key = sortedKeys[index];
        final value = widget.span.attributes[key];
        return Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 2,
                child: SelectableText(
                  key,
                  style: const TextStyle(fontSize: 11, color: AppColors.textPrimary, fontWeight: FontWeight.bold),
                ),
              ),
              Expanded(
                flex: 3,
                child: SelectableText(
                  '$value',
                  style: const TextStyle(fontSize: 11, color: AppColors.textSecondary, fontFamily: 'monospace'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  bool _hasSemanticAttributes() {
    return widget.span.attributes.keys.any((k) => k.startsWith('gen_ai.') || k.startsWith('http.') || k.startsWith('db.'));
  }

  Widget _buildSemanticAttributesPane() {
    final genAiAttrs = <String, dynamic>{};
    final httpAttrs = <String, dynamic>{};
    final dbAttrs = <String, dynamic>{};

    int? inputTokens;
    int? outputTokens;

    for (final entry in widget.span.attributes.entries) {
      if (entry.key.startsWith('gen_ai.')) {
        if (entry.key == 'gen_ai.usage.input_tokens') {
          inputTokens = int.tryParse(entry.value.toString());
        } else if (entry.key == 'gen_ai.usage.output_tokens') {
          outputTokens = int.tryParse(entry.value.toString());
        } else {
          genAiAttrs[entry.key] = entry.value;
        }
      } else if (entry.key.startsWith('http.')) {
        httpAttrs[entry.key] = entry.value;
      } else if (entry.key.startsWith('db.')) {
        dbAttrs[entry.key] = entry.value;
      }
    }

    return ListView(
      padding: const EdgeInsets.all(14),
      children: [
        if (inputTokens != null || outputTokens != null) ...[
          const Text(
            'GenAI Tokens',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            '${(inputTokens ?? 0) / 1000}K (in), ${(outputTokens ?? 0)} (out)',
            style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 16),
        ],

        if (genAiAttrs.isNotEmpty) ...[
          const Text(
            'Related Attributes',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          ..._buildAttributeTable(genAiAttrs),
          const SizedBox(height: 16),
        ],

        if (httpAttrs.isNotEmpty) ...[
          const Text(
            'HTTP Context',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          ..._buildAttributeTable(httpAttrs),
          const SizedBox(height: 16),
        ],

        if (dbAttrs.isNotEmpty) ...[
          const Text(
            'Database Context',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          ..._buildAttributeTable(dbAttrs),
          const SizedBox(height: 16),
        ],
      ],
    );
  }

  List<Widget> _buildAttributeTable(Map<String, dynamic> attributes) {
    final sortedKeys = attributes.keys.toList()..sort();
    return sortedKeys.map((key) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 1,
              child: SelectableText(
                key,
                style: const TextStyle(
                  fontSize: 10,
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            Expanded(
              flex: 1,
              child: SelectableText(
                '${attributes[key]}',
                style: const TextStyle(
                  fontSize: 10,
                  color: AppColors.textSecondary,
                  fontFamily: 'monospace',
                ),
              ),
            ),
          ],
        ),
      );
    }).toList();
  }

  Widget _buildLogsTab() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(strokeWidth: 2),
      );
    }
    if (_logs == null || _logs!.isEmpty) {
      return const Center(
        child: Text('No logs or events found for this span', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(14),
      itemCount: _logs!.length,
      itemBuilder: (context, index) {
        final log = _logs![index];
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.surfaceBorder),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: _getSeverityColor(log.severity).withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      log.severity,
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.bold,
                        color: _getSeverityColor(log.severity)
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    log.timestamp.toLocal().toString(),
                    style: const TextStyle(fontSize: 10, color: AppColors.textMuted),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              if (log.isJsonPayload)
                _buildJsonLogPayload(log.payload)
              else
                SelectableText(
                  log.payload.toString(),
                  style: const TextStyle(fontSize: 11, color: AppColors.textPrimary, fontFamily: 'monospace'),
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildJsonLogPayload(dynamic payload) {
    if (payload is Map) {
      // Very basic formatting for JSON payloads
      final formatted = const JsonEncoder.withIndent('  ').convert(payload);
      return SelectableText(
        formatted,
        style: const TextStyle(fontSize: 11, color: AppColors.textSecondary, fontFamily: 'monospace'),
      );
    }
    return SelectableText(payload.toString());
  }

  Color _getSeverityColor(String severity) {
    switch (severity.toUpperCase()) {
      case 'ERROR':
      case 'CRITICAL':
      case 'EMERGENCY':
        return AppColors.error;
      case 'WARNING':
        return AppColors.warning;
      case 'INFO':
        return AppColors.primaryTeal;
      case 'DEBUG':
        return AppColors.textMuted;
      default:
        return AppColors.textSecondary;
    }
  }

  Widget _buildDetailChip(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: const TextStyle(fontSize: 9, color: AppColors.textMuted, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              fontSize: 11,
              color: color,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}
