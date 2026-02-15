import 'dart:convert';
import 'package:flutter/material.dart';

import '../../services/dashboard_state.dart';
import 'manual_query_bar.dart';
import 'dashboard_card_wrapper.dart';
import 'cards/council_decision_card.dart';
import '../common/explorer_empty_state.dart';

/// Dashboard panel showing council investigation results with premium decision cards.
///
/// Displays a list of council debates and decisions with consensus visualizations.
class LiveCouncilPanel extends StatefulWidget {
  final List<DashboardItem> items;
  final DashboardState dashboardState;

  const LiveCouncilPanel({
    super.key,
    required this.items,
    required this.dashboardState,
  });

  @override
  State<LiveCouncilPanel> createState() => _LiveCouncilPanelState();
}

class _LiveCouncilPanelState extends State<LiveCouncilPanel> {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Top Search Bar
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: ManualQueryBar(
            hintText: 'Search past decisions...',
            dashboardState: widget.dashboardState,
            initialValue: widget.dashboardState.getLastQueryFilter(DashboardDataType.council),
            isLoading: widget.dashboardState.isLoading(DashboardDataType.council),
            onSubmit: (query) {
              widget.dashboardState.setLastQueryFilter(DashboardDataType.council, query);
              // Implementation-specific search logic would go here
            },
          ),
        ),

        // Results Area
        Expanded(
          child: widget.items.isEmpty
              ? const ExplorerEmptyState(
                  icon: Icons.gavel_rounded,
                  title: 'No Council Decisions',
                  description:
                      'The council collects findings from all experts to reach a consensus.\nStart an investigation to see decisions here.',
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: widget.items.length,
                  separatorBuilder: (context, index) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final item = widget.items[index];

                    return DashboardCardWrapper(
                      onClose: () => widget.dashboardState.removeItem(item.id),
                      header: CouncilDecisionCard.buildHeader(item),
                      dataToCopy: const JsonEncoder.withIndent('  ')
                          .convert(item.rawData),
                      child: CouncilDecisionCard(item: item),
                    );
                  },
                ),
        ),
      ],
    );
  }
}
