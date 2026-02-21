import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';

import '../../services/project_service.dart';
import '../../theme/app_theme.dart';

class AgentGraphIframePanel extends StatefulWidget {
  const AgentGraphIframePanel({super.key});

  @override
  State<AgentGraphIframePanel> createState() => _AgentGraphIframePanelState();
}

class _AgentGraphIframePanelState extends State<AgentGraphIframePanel> {
  late String _viewId;
  late String _currentProjectId;

  @override
  void initState() {
    super.initState();
    final projectId =
        ProjectService.instance.selectedProjectId?.isNotEmpty == true
        ? ProjectService.instance.selectedProjectId!
        : 'summitt-gcp';
    _currentProjectId = projectId;
    _viewId = 'agent-graph-iframe-${DateTime.now().millisecondsSinceEpoch}';

    final src = 'http://localhost:5174/graph/?project_id=$_currentProjectId';

    // ignore: undefined_prefixed_name
    ui_web.platformViewRegistry.registerViewFactory(_viewId, (int viewId) {
      final iframe = html.IFrameElement()
        ..src = src
        ..style.border = 'none'
        ..style.height = '100%'
        ..style.width = '100%';
      return iframe;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.backgroundDark,
      child: ValueListenableBuilder(
        valueListenable: ProjectService.instance.selectedProject,
        builder: (context, project, child) {
          return HtmlElementView(viewType: _viewId);
        },
      ),
    );
  }
}
