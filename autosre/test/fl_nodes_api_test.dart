import 'package:fl_nodes/fl_nodes.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('FlNodeEditorController can register prototype and add node', () {
    final controller = FlNodeEditorController();

    // 1. Register prototype
    controller.registerNodePrototype(
      FlNodePrototype(
        idName: 'test_node',
        displayName: (context) => 'Test Node',
        description: (context) => 'Test Description',
        ports: [
          FlDataInputPortPrototype(
            idName: 'in',
            displayName: (context) => 'In',
          ),
        ],
        onExecute: (ports, fields, state, forward, put) async {},
      ),
    );

    expect(controller.nodePrototypes.containsKey('test_node'), true);

    // 2. Add node
    final node = controller.addNode(
      'test_node',
      offset: const Offset(100, 100),
    );

    expect(controller.nodes.containsKey(node.id), true);
    expect(controller.nodes[node.id]!.offset, const Offset(128, 128));

    controller.dispose();
  });
}
