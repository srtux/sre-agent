// ignore_for_file: deprecated_member_use, avoid_web_libraries_in_flutter

import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';

import '../../services/project_service.dart';
import '../../services/service_config.dart';
import '../../theme/app_theme.dart';

class AgentGraphIframePanel extends StatefulWidget {
  const AgentGraphIframePanel({super.key});

  @override
  State<AgentGraphIframePanel> createState() => _AgentGraphIframePanelState();
}

class _AgentGraphIframePanelState extends State<AgentGraphIframePanel> {
  late String _viewId;
  late String _currentProjectId;
  html.IFrameElement? _iframeElement;

  @override
  void initState() {
    super.initState();
    _currentProjectId = ProjectService.instance.selectedProjectId ?? '';
    _viewId = 'agent-graph-iframe-${DateTime.now().millisecondsSinceEpoch}';

    // ignore: undefined_prefixed_name
    ui_web.platformViewRegistry.registerViewFactory(_viewId, (int viewId) {
      final baseUrl = ServiceConfig.agentGraphBaseUrl;
      final dynamicSrc = _currentProjectId.isNotEmpty
          ? '$baseUrl/graph/?project_id=$_currentProjectId'
          : 'about:blank';

      print(
        '[Flutter Iframe DEBUG] registerViewFactory called! dynamicSrc=$dynamicSrc',
      );

      _iframeElement = html.IFrameElement()
        ..id = _viewId
        ..src = dynamicSrc
        ..style.border = 'none'
        ..style.height = '100%'
        ..style.width = '100%';
      return _iframeElement!;
    });
  }

  void _updateIframeSrc(String newProjectId) {
    print(
      '[Flutter Iframe DEBUG] _updateIframeSrc called! newProjectId=$newProjectId, old=_currentProjectId',
    );
    if (newProjectId != _currentProjectId) {
      _currentProjectId = newProjectId;
      if (_iframeElement != null) {
        final baseUrl = ServiceConfig.agentGraphBaseUrl;
        final newSrc = '$baseUrl/graph/?project_id=$_currentProjectId';
        print('[Flutter Iframe DEBUG] SETTING iframe element src to: $newSrc');
        _iframeElement!.src = newSrc;
      } else {
        print(
          '[Flutter Iframe DEBUG] ERROR: _iframeElement is null, cannot update src!',
        );
      }
    } else {
      print('[Flutter Iframe DEBUG] Ignored update, project ID is the same.');
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
              : '';

          if (newProject.isEmpty) {
            return const Center(
              child: Text(
                'Please select a project from the top menu to view the agent graph.',
                style: TextStyle(color: AppColors.textSecondary),
              ),
            );
          }

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
