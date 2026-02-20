import 'dart:ui';

import 'package:autosre/features/agent_graph/presentation/back_edge_painter.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('BackEdgePainter', () {
    test('shouldRepaint returns true when phase changes', () {
      final painter1 = BackEdgePainter(
        edges: const [],
        marchingAntsPhase: 0.0,
      );
      final painter2 = BackEdgePainter(
        edges: const [],
        marchingAntsPhase: 0.5,
      );

      expect(painter1.shouldRepaint(painter2), isTrue);
    });

    test('shouldRepaint returns false when nothing changes', () {
      final edges = [
        const BackEdgePath(
          start: Offset(0, 0),
          end: Offset(100, 100),
          color: Color(0xFF00FF00),
          sourceId: 'A',
          targetId: 'B',
        ),
      ];

      final painter1 = BackEdgePainter(
        edges: edges,
        marchingAntsPhase: 0.3,
      );
      final painter2 = BackEdgePainter(
        edges: edges,
        marchingAntsPhase: 0.3,
      );

      expect(painter1.shouldRepaint(painter2), isFalse);
    });

    test('shouldRepaint returns true when highlightedPath changes', () {
      final painter1 = BackEdgePainter(
        edges: const [],
        marchingAntsPhase: 0.0,
        highlightedPath: const {'A'},
      );
      final painter2 = BackEdgePainter(
        edges: const [],
        marchingAntsPhase: 0.0,
        highlightedPath: const {'B'},
      );

      expect(painter1.shouldRepaint(painter2), isTrue);
    });

    test('shouldRepaint returns true when dimOpacity changes', () {
      final painter1 = BackEdgePainter(
        edges: const [],
        marchingAntsPhase: 0.0,
        dimOpacity: 0.2,
      );
      final painter2 = BackEdgePainter(
        edges: const [],
        marchingAntsPhase: 0.0,
        dimOpacity: 0.5,
      );

      expect(painter1.shouldRepaint(painter2), isTrue);
    });

    test('shouldRepaint returns false when highlightedPath is same instance', () {
      const path = {'A', 'B'};
      final painter1 = BackEdgePainter(
        edges: const [],
        marchingAntsPhase: 0.0,
        highlightedPath: path,
      );
      final painter2 = BackEdgePainter(
        edges: const [],
        marchingAntsPhase: 0.0,
        highlightedPath: path,
      );

      expect(painter1.shouldRepaint(painter2), isFalse);
    });

    test('shouldRepaint returns true when edges list changes', () {
      final edges1 = [
        const BackEdgePath(
          start: Offset(0, 0),
          end: Offset(100, 100),
          color: Color(0xFF00FF00),
          sourceId: 'A',
          targetId: 'B',
        ),
      ];
      final edges2 = <BackEdgePath>[];

      final painter1 = BackEdgePainter(
        edges: edges1,
        marchingAntsPhase: 0.0,
      );
      final painter2 = BackEdgePainter(
        edges: edges2,
        marchingAntsPhase: 0.0,
      );

      expect(painter1.shouldRepaint(painter2), isTrue);
    });
  });

  group('BackEdgePath', () {
    test('stores all properties correctly', () {
      const path = BackEdgePath(
        start: Offset(10, 20),
        end: Offset(30, 40),
        color: Color(0xFFFF0000),
        thickness: 3.0,
        sourceId: 'src',
        targetId: 'tgt',
        edgeIndex: 2,
      );

      expect(path.start, const Offset(10, 20));
      expect(path.end, const Offset(30, 40));
      expect(path.thickness, 3.0);
      expect(path.sourceId, 'src');
      expect(path.targetId, 'tgt');
      expect(path.edgeIndex, 2);
    });

    test('has sensible defaults', () {
      const path = BackEdgePath(
        start: Offset(0, 0),
        end: Offset(100, 100),
        color: Color(0xFF00FF00),
        sourceId: 'A',
        targetId: 'B',
      );

      expect(path.thickness, 2.0);
      expect(path.edgeIndex, 0);
    });
  });
}
