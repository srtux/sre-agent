import 'dart:ui';

/// Manages sprouting/collapsing animation interpolation for graph layout
/// transitions.
///
/// Pure logic — no Flutter widget dependencies. Computes interpolated
/// positions and opacities for nodes transitioning between two layout states.
class GraphTransitionState {
  /// Positions from the previous layout.
  final Map<String, Offset> previousPositions;

  /// Target positions in the new layout.
  final Map<String, Offset> targetPositions;

  /// Nodes appearing (were not visible, now are).
  final Set<String> sproutingIds;

  /// Nodes disappearing (were visible, now are not).
  final Set<String> collapsingIds;

  /// For sprouting nodes: nodeId → parentId (animation origin).
  final Map<String, String> parentOfSprouting;

  /// For collapsing nodes: nodeId → parentId (animation destination).
  final Map<String, String> parentOfCollapsing;

  const GraphTransitionState._({
    required this.previousPositions,
    required this.targetPositions,
    required this.sproutingIds,
    required this.collapsingIds,
    required this.parentOfSprouting,
    required this.parentOfCollapsing,
  });

  /// A no-op transition with no animation needed.
  static const empty = GraphTransitionState._(
    previousPositions: {},
    targetPositions: {},
    sproutingIds: {},
    collapsingIds: {},
    parentOfSprouting: {},
    parentOfCollapsing: {},
  );

  /// Compute transition state from [oldPositions] → [newPositions].
  ///
  /// - **Sprouting**: nodes in [newVisibleIds] but not in [oldVisibleIds].
  ///   Start at parent position, animate to target.
  /// - **Collapsing**: nodes in [oldVisibleIds] but not in [newVisibleIds].
  ///   Start at previous position, animate to parent position.
  /// - **Persisting**: nodes in both sets. Lerp between old and new positions.
  ///
  /// [childToParent] maps each node to its parent in the DAG.
  factory GraphTransitionState.compute({
    required Map<String, Offset> oldPositions,
    required Map<String, Offset> newPositions,
    required Set<String> oldVisibleIds,
    required Set<String> newVisibleIds,
    required Map<String, String> childToParent,
  }) {
    final sproutingIds = <String>{};
    final collapsingIds = <String>{};
    final parentOfSprouting = <String, String>{};
    final parentOfCollapsing = <String, String>{};

    // Detect sprouting nodes.
    for (final id in newVisibleIds) {
      if (!oldVisibleIds.contains(id)) {
        sproutingIds.add(id);
        final parentId = childToParent[id];
        if (parentId != null) {
          parentOfSprouting[id] = parentId;
        }
      }
    }

    // Detect collapsing nodes.
    for (final id in oldVisibleIds) {
      if (!newVisibleIds.contains(id)) {
        collapsingIds.add(id);
        final parentId = childToParent[id];
        if (parentId != null) {
          parentOfCollapsing[id] = parentId;
        }
      }
    }

    return GraphTransitionState._(
      previousPositions: Map.unmodifiable(oldPositions),
      targetPositions: Map.unmodifiable(newPositions),
      sproutingIds: Set.unmodifiable(sproutingIds),
      collapsingIds: Set.unmodifiable(collapsingIds),
      parentOfSprouting: Map.unmodifiable(parentOfSprouting),
      parentOfCollapsing: Map.unmodifiable(parentOfCollapsing),
    );
  }

  /// Interpolated position at animation progress [t] ∈ [0, 1].
  ///
  /// - **Persisting**: `lerp(previous, target, t)`
  /// - **Sprouting**: `lerp(parentCenter, target, t)`
  /// - **Collapsing**: `lerp(previous, parentCenter, t)`
  Offset positionAt(String nodeId, double t) {
    if (sproutingIds.contains(nodeId)) {
      final parentId = parentOfSprouting[nodeId];
      // Start from parent's position (prefer new position, fall back to old).
      final parentPos = targetPositions[parentId] ??
          previousPositions[parentId] ??
          Offset.zero;
      final target = targetPositions[nodeId] ?? parentPos;
      return Offset.lerp(parentPos, target, t)!;
    }

    if (collapsingIds.contains(nodeId)) {
      final parentId = parentOfCollapsing[nodeId];
      // End at parent's position (prefer new position, fall back to old).
      final parentPos = targetPositions[parentId] ??
          previousPositions[parentId] ??
          Offset.zero;
      final prev = previousPositions[nodeId] ?? parentPos;
      return Offset.lerp(prev, parentPos, t)!;
    }

    // Persisting node — simple lerp.
    final prev = previousPositions[nodeId] ?? targetPositions[nodeId];
    final target = targetPositions[nodeId] ?? previousPositions[nodeId];
    if (prev == null || target == null) return Offset.zero;
    return Offset.lerp(prev, target, t)!;
  }

  /// Opacity at animation progress [t].
  ///
  /// - **Sprouting**: `t` (fade in from 0 → 1)
  /// - **Collapsing**: `1 - t` (fade out from 1 → 0)
  /// - **Persisting**: `1.0`
  double opacityAt(String nodeId, double t) {
    if (sproutingIds.contains(nodeId)) return t;
    if (collapsingIds.contains(nodeId)) return 1.0 - t;
    return 1.0;
  }

  /// All node IDs that should be rendered at progress [t].
  ///
  /// Includes collapsing nodes until `t >= 1.0`, at which point they are
  /// removed from the render tree.
  Set<String> visibleIdsAt(double t) {
    final ids = <String>{};

    // All target (new) nodes.
    ids.addAll(targetPositions.keys);

    // Add collapsing nodes while animation is in progress.
    if (t < 1.0) {
      ids.addAll(collapsingIds);
    }

    return ids;
  }
}
