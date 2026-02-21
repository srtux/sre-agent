// ignore_for_file: deprecated_member_use, avoid_web_libraries_in_flutter

import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/foundation.dart';
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
    _currentProjectId =
        ProjectService.instance.selectedProjectId ?? 'my-project';
    if (_currentProjectId.isEmpty) _currentProjectId = 'my-project';
    _viewId = 'agent-graph-iframe-${DateTime.now().millisecondsSinceEpoch}';

    final String baseUrl = kDebugMode ? 'http://localhost:5174' : '';
    final src = '$baseUrl/graph/?project_id=$_currentProjectId';

    // ignore: undefined_prefixed_name
    ui_web.platformViewRegistry.registerViewFactory(_viewId, (int viewId) {
      final iframe = html.IFrameElement()
        ..id = _viewId
        ..src = src
        ..style.border = 'none'
        ..style.height = '100%'
        ..style.width = '100%';
      return iframe;
    });
  }

  void _updateIframeSrc(String newProjectId) {
    if (newProjectId != _currentProjectId) {
      _currentProjectId = newProjectId;
      final iframe =
          html.document.getElementById(_viewId) as html.IFrameElement?;
      if (iframe != null) {
        final String baseUrl = kDebugMode ? 'http://localhost:5174' : '';
        iframe.src = '$baseUrl/graph/?project_id=$_currentProjectId';
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.backgroundDark,
      child: ValueListenableBuilder(
        valueListenable: ProjectService.instance.selectedProject,
        builder: (context, project, child) {
          final newProject = project?.projectId.isNotEmpty == true
              ? project!.projectId
              : 'my-project';
          // Schedule URL update after the build phase
          WidgetsBinding.instance.addPostFrameCallback((_) {
            _updateIframeSrc(newProject);
          });
          return HtmlElementView(viewType: _viewId);
        },
      ),
    );
  }
}
