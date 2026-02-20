import 'package:autosre/features/agent_graph/presentation/graph_animation_controller.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('GraphTransitionState', () {
    group('compute', () {
      test('detects sprouting nodes', () {
        final state = GraphTransitionState.compute(
          oldPositions: {'A': const Offset(0, 0)},
          newPositions: {
            'A': const Offset(0, 0),
            'B': const Offset(100, 0),
          },
          oldVisibleIds: {'A'},
          newVisibleIds: {'A', 'B'},
          childToParent: {'B': 'A'},
        );

        expect(state.sproutingIds, contains('B'));
        expect(state.collapsingIds, isEmpty);
        expect(state.parentOfSprouting['B'], 'A');
      });

      test('detects collapsing nodes', () {
        final state = GraphTransitionState.compute(
          oldPositions: {
            'A': const Offset(0, 0),
            'B': const Offset(100, 0),
          },
          newPositions: {'A': const Offset(0, 0)},
          oldVisibleIds: {'A', 'B'},
          newVisibleIds: {'A'},
          childToParent: {'B': 'A'},
        );

        expect(state.collapsingIds, contains('B'));
        expect(state.sproutingIds, isEmpty);
        expect(state.parentOfCollapsing['B'], 'A');
      });

      test('persisting nodes are neither sprouting nor collapsing', () {
        final state = GraphTransitionState.compute(
          oldPositions: {'A': const Offset(0, 0)},
          newPositions: {'A': const Offset(50, 50)},
          oldVisibleIds: {'A'},
          newVisibleIds: {'A'},
          childToParent: {},
        );

        expect(state.sproutingIds, isEmpty);
        expect(state.collapsingIds, isEmpty);
      });
    });

    group('positionAt', () {
      test('sprouting node starts at parent position', () {
        final state = GraphTransitionState.compute(
          oldPositions: {'A': const Offset(0, 0)},
          newPositions: {
            'A': const Offset(0, 0),
            'B': const Offset(100, 0),
          },
          oldVisibleIds: {'A'},
          newVisibleIds: {'A', 'B'},
          childToParent: {'B': 'A'},
        );

        // At t=0, sprouting node B should be at parent A's position.
        final pos0 = state.positionAt('B', 0.0);
        expect(pos0.dx, 0.0);
        expect(pos0.dy, 0.0);

        // At t=1, sprouting node B should be at its target.
        final pos1 = state.positionAt('B', 1.0);
        expect(pos1.dx, 100.0);
        expect(pos1.dy, 0.0);
      });

      test('sprouting node at t=0.5 is halfway', () {
        final state = GraphTransitionState.compute(
          oldPositions: {'A': const Offset(0, 0)},
          newPositions: {
            'A': const Offset(0, 0),
            'B': const Offset(100, 0),
          },
          oldVisibleIds: {'A'},
          newVisibleIds: {'A', 'B'},
          childToParent: {'B': 'A'},
        );

        final pos = state.positionAt('B', 0.5);
        expect(pos.dx, closeTo(50.0, 0.01));
      });

      test('collapsing node ends at parent position', () {
        final state = GraphTransitionState.compute(
          oldPositions: {
            'A': const Offset(0, 0),
            'B': const Offset(100, 0),
          },
          newPositions: {'A': const Offset(0, 0)},
          oldVisibleIds: {'A', 'B'},
          newVisibleIds: {'A'},
          childToParent: {'B': 'A'},
        );

        // At t=0, collapsing node B should be at its previous position.
        final pos0 = state.positionAt('B', 0.0);
        expect(pos0.dx, 100.0);

        // At t=1, collapsing node B should be at parent A's position.
        final pos1 = state.positionAt('B', 1.0);
        expect(pos1.dx, 0.0);
      });

      test('persisting node lerps between old and new', () {
        final state = GraphTransitionState.compute(
          oldPositions: {'A': const Offset(0, 0)},
          newPositions: {'A': const Offset(200, 100)},
          oldVisibleIds: {'A'},
          newVisibleIds: {'A'},
          childToParent: {},
        );

        final pos0 = state.positionAt('A', 0.0);
        expect(pos0, const Offset(0, 0));

        final pos05 = state.positionAt('A', 0.5);
        expect(pos05.dx, closeTo(100, 0.01));
        expect(pos05.dy, closeTo(50, 0.01));

        final pos1 = state.positionAt('A', 1.0);
        expect(pos1, const Offset(200, 100));
      });
    });

    group('opacityAt', () {
      test('sprouting node fades in', () {
        final state = GraphTransitionState.compute(
          oldPositions: {},
          newPositions: {'B': const Offset(0, 0)},
          oldVisibleIds: <String>{},
          newVisibleIds: {'B'},
          childToParent: {},
        );

        expect(state.opacityAt('B', 0.0), 0.0);
        expect(state.opacityAt('B', 0.5), 0.5);
        expect(state.opacityAt('B', 1.0), 1.0);
      });

      test('collapsing node fades out', () {
        final state = GraphTransitionState.compute(
          oldPositions: {'B': const Offset(0, 0)},
          newPositions: {},
          oldVisibleIds: {'B'},
          newVisibleIds: <String>{},
          childToParent: {},
        );

        expect(state.opacityAt('B', 0.0), 1.0);
        expect(state.opacityAt('B', 0.5), 0.5);
        expect(state.opacityAt('B', 1.0), 0.0);
      });

      test('persisting node always fully opaque', () {
        final state = GraphTransitionState.compute(
          oldPositions: {'A': const Offset(0, 0)},
          newPositions: {'A': const Offset(100, 0)},
          oldVisibleIds: {'A'},
          newVisibleIds: {'A'},
          childToParent: {},
        );

        expect(state.opacityAt('A', 0.0), 1.0);
        expect(state.opacityAt('A', 0.5), 1.0);
        expect(state.opacityAt('A', 1.0), 1.0);
      });
    });

    group('visibleIdsAt', () {
      test('includes collapsing nodes before t=1', () {
        final state = GraphTransitionState.compute(
          oldPositions: {
            'A': const Offset(0, 0),
            'B': const Offset(100, 0),
          },
          newPositions: {'A': const Offset(0, 0)},
          oldVisibleIds: {'A', 'B'},
          newVisibleIds: {'A'},
          childToParent: {'B': 'A'},
        );

        expect(state.visibleIdsAt(0.0), containsAll(['A', 'B']));
        expect(state.visibleIdsAt(0.5), containsAll(['A', 'B']));
      });

      test('excludes collapsing nodes at t=1', () {
        final state = GraphTransitionState.compute(
          oldPositions: {
            'A': const Offset(0, 0),
            'B': const Offset(100, 0),
          },
          newPositions: {'A': const Offset(0, 0)},
          oldVisibleIds: {'A', 'B'},
          newVisibleIds: {'A'},
          childToParent: {'B': 'A'},
        );

        final ids = state.visibleIdsAt(1.0);
        expect(ids, contains('A'));
        expect(ids, isNot(contains('B')));
      });

      test('includes sprouting nodes at all t values', () {
        final state = GraphTransitionState.compute(
          oldPositions: {'A': const Offset(0, 0)},
          newPositions: {
            'A': const Offset(0, 0),
            'B': const Offset(100, 0),
          },
          oldVisibleIds: {'A'},
          newVisibleIds: {'A', 'B'},
          childToParent: {'B': 'A'},
        );

        expect(state.visibleIdsAt(0.0), containsAll(['A', 'B']));
        expect(state.visibleIdsAt(1.0), containsAll(['A', 'B']));
      });
    });

    test('empty transition state has no nodes', () {
      const state = GraphTransitionState.empty;
      expect(state.sproutingIds, isEmpty);
      expect(state.collapsingIds, isEmpty);
      expect(state.visibleIdsAt(0.0), isEmpty);
    });

    test('sprouting node without parent starts at Offset.zero', () {
      final state = GraphTransitionState.compute(
        oldPositions: {},
        newPositions: {'B': const Offset(100, 50)},
        oldVisibleIds: <String>{},
        newVisibleIds: {'B'},
        childToParent: {}, // No parent for B
      );

      expect(state.sproutingIds, contains('B'));
      // Without a parent, sprout starts at Offset.zero.
      final pos0 = state.positionAt('B', 0.0);
      expect(pos0, Offset.zero);

      final pos1 = state.positionAt('B', 1.0);
      expect(pos1, const Offset(100, 50));
    });

    test('collapsing node without parent ends at Offset.zero', () {
      final state = GraphTransitionState.compute(
        oldPositions: {'B': const Offset(100, 50)},
        newPositions: {},
        oldVisibleIds: {'B'},
        newVisibleIds: <String>{},
        childToParent: {}, // No parent for B
      );

      expect(state.collapsingIds, contains('B'));
      final pos0 = state.positionAt('B', 0.0);
      expect(pos0, const Offset(100, 50));

      final pos1 = state.positionAt('B', 1.0);
      expect(pos1, Offset.zero);
    });

    test('unknown node returns Offset.zero', () {
      const state = GraphTransitionState.empty;
      expect(state.positionAt('nonexistent', 0.5), Offset.zero);
    });

    test('unknown node has opacity 1.0', () {
      const state = GraphTransitionState.empty;
      expect(state.opacityAt('nonexistent', 0.5), 1.0);
    });

    test('simultaneous sprouting and collapsing', () {
      // A persists, B collapses, C sprouts
      final state = GraphTransitionState.compute(
        oldPositions: {
          'A': const Offset(0, 0),
          'B': const Offset(100, 0),
        },
        newPositions: {
          'A': const Offset(0, 0),
          'C': const Offset(200, 0),
        },
        oldVisibleIds: {'A', 'B'},
        newVisibleIds: {'A', 'C'},
        childToParent: {'B': 'A', 'C': 'A'},
      );

      expect(state.sproutingIds, contains('C'));
      expect(state.collapsingIds, contains('B'));
      expect(state.sproutingIds, isNot(contains('A')));
      expect(state.collapsingIds, isNot(contains('A')));

      // At t=0.5, all three should be visible.
      final ids = state.visibleIdsAt(0.5);
      expect(ids, containsAll(['A', 'B', 'C']));

      // At t=1.0, B should be gone.
      final idsFinal = state.visibleIdsAt(1.0);
      expect(idsFinal, containsAll(['A', 'C']));
      expect(idsFinal, isNot(contains('B')));
    });
  });
}
