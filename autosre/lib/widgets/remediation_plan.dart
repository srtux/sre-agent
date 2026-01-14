
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/adk_schema.dart';

class RemediationPlanWidget extends StatelessWidget {
  final RemediationPlan plan;

  const RemediationPlanWidget({super.key, required this.plan});

  Color _getRiskColor(String risk, BuildContext context) {
    switch (risk.toLowerCase()) {
      case 'high':
        return Theme.of(context).colorScheme.error;
      case 'medium':
        return Colors.orange;
      case 'low':
        return Colors.green;
      default:
        return Theme.of(context).colorScheme.primary;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
            ListTile(
                leading: Icon(Icons.build_circle, color: _getRiskColor(plan.risk, context)),
                title: Text(plan.issue, style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text("Risk Level: ${plan.risk.toUpperCase()}", style: TextStyle(color: _getRiskColor(plan.risk, context))),
            ),
            const Divider(),
            ...plan.steps.map((step) => _buildStep(step, context)),
        ],
      ),
    );
  }

  Widget _buildStep(RemediationStep step, BuildContext context) {
      return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                  Text(step.description, style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 8),
                  Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(4),
                      ),
                      child: Row(
                          children: [
                              Expanded(child: SelectableText(step.command, style: const TextStyle(fontFamily: 'monospace'))),
                              IconButton(
                                  icon: const Icon(Icons.copy, size: 16),
                                  onPressed: () {
                                      Clipboard.setData(ClipboardData(text: step.command));
                                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Command copied")));
                                  },
                                  tooltip: "Copy Command",
                              )
                          ],
                      ),
                  )
              ],
          ),
      );
  }
}
