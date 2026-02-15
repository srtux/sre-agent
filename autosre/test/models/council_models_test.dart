import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/models/adk_schema.dart';

void main() {
  // ===========================================================================
  // PanelFinding
  // ===========================================================================
  group('PanelFinding', () {
    test('fromJson parses valid data', () {
      final finding = PanelFinding.fromJson({
        'panel': 'trace',
        'summary': 'High latency in checkout service',
        'severity': 'warning',
        'confidence': 0.85,
        'evidence': ['Trace abc123: 2.5s latency'],
        'recommended_actions': ['Scale checkout pods'],
      });
      expect(finding.panel, 'trace');
      expect(finding.summary, 'High latency in checkout service');
      expect(finding.severity, 'warning');
      expect(finding.confidence, 0.85);
      expect(finding.evidence.length, 1);
      expect(finding.recommendedActions.length, 1);
    });

    test('fromJson provides defaults', () {
      final finding = PanelFinding.fromJson(const {});
      expect(finding.panel, 'unknown');
      expect(finding.summary, '');
      expect(finding.severity, 'info');
      expect(finding.confidence, 0.0);
      expect(finding.evidence, isEmpty);
      expect(finding.recommendedActions, isEmpty);
    });

    test('displayName maps correctly', () {
      expect(
        PanelFinding(panel: 'trace', summary: '', severity: '', confidence: 0, evidence: [], recommendedActions: []).displayName,
        'Trace Analysis',
      );
      expect(
        PanelFinding(panel: 'metrics', summary: '', severity: '', confidence: 0, evidence: [], recommendedActions: []).displayName,
        'Metrics Analysis',
      );
      expect(
        PanelFinding(panel: 'logs', summary: '', severity: '', confidence: 0, evidence: [], recommendedActions: []).displayName,
        'Logs Analysis',
      );
      expect(
        PanelFinding(panel: 'alerts', summary: '', severity: '', confidence: 0, evidence: [], recommendedActions: []).displayName,
        'Alerts Analysis',
      );
      expect(
        PanelFinding(panel: 'custom', summary: '', severity: '', confidence: 0, evidence: [], recommendedActions: []).displayName,
        'custom',
      );
    });

    test('iconName maps correctly', () {
      expect(
        PanelFinding(panel: 'trace', summary: '', severity: '', confidence: 0, evidence: [], recommendedActions: []).iconName,
        'timeline',
      );
      expect(
        PanelFinding(panel: 'unknown', summary: '', severity: '', confidence: 0, evidence: [], recommendedActions: []).iconName,
        'help',
      );
    });
  });

  // ===========================================================================
  // CriticReport
  // ===========================================================================
  group('CriticReport', () {
    test('fromJson parses valid data', () {
      final report = CriticReport.fromJson({
        'agreements': ['DB is primary bottleneck'],
        'contradictions': ['Metrics show healthy but traces show errors'],
        'gaps': ['Missing network analysis'],
        'revised_confidence': 0.72,
      });
      expect(report.agreements.length, 1);
      expect(report.contradictions.length, 1);
      expect(report.gaps.length, 1);
      expect(report.revisedConfidence, 0.72);
    });

    test('fromJson provides defaults', () {
      final report = CriticReport.fromJson(const {});
      expect(report.agreements, isEmpty);
      expect(report.contradictions, isEmpty);
      expect(report.gaps, isEmpty);
      expect(report.revisedConfidence, 0.0);
    });

    test('hasContradictions is true when contradictions exist', () {
      final report = CriticReport(
        agreements: [], contradictions: ['conflict'], gaps: [],
        revisedConfidence: 0.5,
      );
      expect(report.hasContradictions, isTrue);
    });

    test('hasGaps is true when gaps exist', () {
      final report = CriticReport(
        agreements: [], contradictions: [], gaps: ['missing data'],
        revisedConfidence: 0.5,
      );
      expect(report.hasGaps, isTrue);
    });

    test('hasStrongAgreement when 2+ agreements and no contradictions', () {
      final report = CriticReport(
        agreements: ['a1', 'a2'], contradictions: [], gaps: [],
        revisedConfidence: 0.9,
      );
      expect(report.hasStrongAgreement, isTrue);
    });

    test('hasStrongAgreement false with contradictions', () {
      final report = CriticReport(
        agreements: ['a1', 'a2'], contradictions: ['c1'], gaps: [],
        revisedConfidence: 0.5,
      );
      expect(report.hasStrongAgreement, isFalse);
    });
  });

  // ===========================================================================
  // CouncilAgentType
  // ===========================================================================
  group('CouncilAgentType', () {
    test('fromString maps correctly', () {
      expect(CouncilAgentType.fromString('root'), CouncilAgentType.root);
      expect(CouncilAgentType.fromString('orchestrator'), CouncilAgentType.orchestrator);
      expect(CouncilAgentType.fromString('panel'), CouncilAgentType.panel);
      expect(CouncilAgentType.fromString('critic'), CouncilAgentType.critic);
      expect(CouncilAgentType.fromString('synthesizer'), CouncilAgentType.synthesizer);
      expect(CouncilAgentType.fromString('sub_agent'), CouncilAgentType.subAgent);
      expect(CouncilAgentType.fromString('subagent'), CouncilAgentType.subAgent);
    });

    test('fromString defaults to subAgent for unknown', () {
      expect(CouncilAgentType.fromString('unknown_type'), CouncilAgentType.subAgent);
      expect(CouncilAgentType.fromString(''), CouncilAgentType.subAgent);
    });

    test('fromString is case-insensitive', () {
      expect(CouncilAgentType.fromString('ROOT'), CouncilAgentType.root);
      expect(CouncilAgentType.fromString('Panel'), CouncilAgentType.panel);
    });

    test('displayName provides human-readable names', () {
      expect(CouncilAgentType.root.displayName, 'Root Agent');
      expect(CouncilAgentType.orchestrator.displayName, 'Orchestrator');
      expect(CouncilAgentType.panel.displayName, 'Expert Panel');
      expect(CouncilAgentType.critic.displayName, 'Critic');
      expect(CouncilAgentType.synthesizer.displayName, 'Synthesizer');
      expect(CouncilAgentType.subAgent.displayName, 'Sub-Agent');
    });
  });

  // ===========================================================================
  // ToolCallRecord
  // ===========================================================================
  group('ToolCallRecord', () {
    test('fromJson parses valid data', () {
      final record = ToolCallRecord.fromJson({
        'call_id': 'c1',
        'tool_name': 'fetch_trace',
        'args_summary': 'trace_id=abc',
        'result_summary': '15 spans found',
        'status': 'completed',
        'duration_ms': 250,
        'timestamp': '2026-01-01T10:00:00Z',
        'dashboard_category': 'traces',
      });
      expect(record.callId, 'c1');
      expect(record.toolName, 'fetch_trace');
      expect(record.status, 'completed');
      expect(record.durationMs, 250);
      expect(record.dashboardCategory, 'traces');
      expect(record.isCompleted, isTrue);
      expect(record.hasDashboardData, isTrue);
    });

    test('fromJson provides defaults', () {
      final record = ToolCallRecord.fromJson(const {});
      expect(record.callId, '');
      expect(record.toolName, '');
      expect(record.status, 'completed');
      expect(record.durationMs, 0);
      expect(record.dashboardCategory, isNull);
    });

    test('status helpers work correctly', () {
      expect(ToolCallRecord(callId: '', toolName: '', status: 'error').isError, isTrue);
      expect(ToolCallRecord(callId: '', toolName: '', status: 'pending').isPending, isTrue);
      expect(ToolCallRecord(callId: '', toolName: '', status: 'completed').isCompleted, isTrue);
    });
  });

  // ===========================================================================
  // LLMCallRecord
  // ===========================================================================
  group('LLMCallRecord', () {
    test('fromJson parses valid data', () {
      final record = LLMCallRecord.fromJson({
        'call_id': 'l1',
        'model': 'gemini-2.0-flash',
        'input_tokens': 1500,
        'output_tokens': 500,
        'duration_ms': 800,
        'timestamp': '2026-01-01T10:00:00Z',
      });
      expect(record.callId, 'l1');
      expect(record.model, 'gemini-2.0-flash');
      expect(record.inputTokens, 1500);
      expect(record.outputTokens, 500);
      expect(record.totalTokens, 2000);
      expect(record.durationMs, 800);
    });

    test('fromJson provides defaults', () {
      final record = LLMCallRecord.fromJson(const {});
      expect(record.callId, '');
      expect(record.model, '');
      expect(record.inputTokens, 0);
      expect(record.outputTokens, 0);
      expect(record.totalTokens, 0);
    });
  });

  // ===========================================================================
  // CouncilAgentActivity
  // ===========================================================================
  group('CouncilAgentActivity', () {
    test('fromJson parses valid data', () {
      final activity = CouncilAgentActivity.fromJson({
        'agent_id': 'agent-1',
        'agent_name': 'trace_panel',
        'agent_type': 'panel',
        'parent_id': 'orchestrator-1',
        'status': 'completed',
        'started_at': '2026-01-01T10:00:00Z',
        'completed_at': '2026-01-01T10:00:05Z',
        'tool_calls': [
          {'call_id': 'c1', 'tool_name': 'fetch_trace'},
        ],
        'llm_calls': [
          {'call_id': 'l1', 'model': 'gemini'},
        ],
        'output_summary': 'Found high latency',
      });
      expect(activity.agentId, 'agent-1');
      expect(activity.agentName, 'trace_panel');
      expect(activity.agentType, CouncilAgentType.panel);
      expect(activity.parentId, 'orchestrator-1');
      expect(activity.isCompleted, isTrue);
      expect(activity.isRoot, isFalse);
      expect(activity.totalToolCalls, 1);
      expect(activity.totalLLMCalls, 1);
    });

    test('fromJson provides defaults', () {
      final activity = CouncilAgentActivity.fromJson(const {});
      expect(activity.agentId, '');
      expect(activity.agentName, '');
      expect(activity.agentType, CouncilAgentType.subAgent);
      expect(activity.status, 'pending');
      expect(activity.toolCalls, isEmpty);
      expect(activity.llmCalls, isEmpty);
    });

    test('isRoot when parentId is null', () {
      final activity = CouncilAgentActivity(
        agentId: 'root', agentName: 'root', agentType: CouncilAgentType.root,
      );
      expect(activity.isRoot, isTrue);
    });

    test('status helpers work correctly', () {
      expect(
        CouncilAgentActivity(agentId: '', agentName: '', agentType: CouncilAgentType.root, status: 'running').isRunning,
        isTrue,
      );
      expect(
        CouncilAgentActivity(agentId: '', agentName: '', agentType: CouncilAgentType.root, status: 'error').hasError,
        isTrue,
      );
    });

    test('errorCount counts tool errors', () {
      final activity = CouncilAgentActivity(
        agentId: 'a1', agentName: 'test', agentType: CouncilAgentType.panel,
        toolCalls: [
          ToolCallRecord(callId: 'c1', toolName: 't1', status: 'completed'),
          ToolCallRecord(callId: 'c2', toolName: 't2', status: 'error'),
          ToolCallRecord(callId: 'c3', toolName: 't3', status: 'error'),
        ],
      );
      expect(activity.errorCount, 2);
    });

    test('getToolCallsForCategory filters by category', () {
      final activity = CouncilAgentActivity(
        agentId: 'a1', agentName: 'test', agentType: CouncilAgentType.panel,
        toolCalls: [
          ToolCallRecord(callId: 'c1', toolName: 't1', dashboardCategory: 'traces'),
          ToolCallRecord(callId: 'c2', toolName: 't2', dashboardCategory: 'metrics'),
          ToolCallRecord(callId: 'c3', toolName: 't3', dashboardCategory: 'traces'),
        ],
      );
      expect(activity.getToolCallsForCategory('traces').length, 2);
      expect(activity.getToolCallsForCategory('metrics').length, 1);
      expect(activity.getToolCallsForCategory('logs').length, 0);
    });

    test('iconName maps agent types correctly', () {
      expect(
        CouncilAgentActivity(agentId: '', agentName: '', agentType: CouncilAgentType.root).iconName,
        'account_tree',
      );
      expect(
        CouncilAgentActivity(agentId: '', agentName: '', agentType: CouncilAgentType.panel).iconName,
        'psychology',
      );
    });
  });

  // ===========================================================================
  // CouncilActivityGraph
  // ===========================================================================
  group('CouncilActivityGraph', () {
    CouncilActivityGraph makeGraph() => CouncilActivityGraph.fromJson({
      'investigation_id': 'inv-1',
      'mode': 'debate',
      'started_at': '2026-01-01T10:00:00Z',
      'completed_at': '2026-01-01T10:01:00Z',
      'debate_rounds': 2,
      'agents': [
        {
          'agent_id': 'root-1',
          'agent_name': 'sre_agent',
          'agent_type': 'root',
          'status': 'completed',
          'tool_calls': [{'call_id': 'c1', 'tool_name': 'route', 'dashboard_category': 'traces'}],
          'llm_calls': [{'call_id': 'l1', 'model': 'gemini'}],
        },
        {
          'agent_id': 'panel-1',
          'agent_name': 'trace_panel',
          'agent_type': 'panel',
          'parent_id': 'root-1',
          'status': 'completed',
          'tool_calls': [{'call_id': 'c2', 'tool_name': 'fetch_trace', 'dashboard_category': 'traces'}],
        },
        {
          'agent_id': 'critic-1',
          'agent_name': 'critic',
          'agent_type': 'critic',
          'parent_id': 'root-1',
          'status': 'completed',
        },
        {
          'agent_id': 'synth-1',
          'agent_name': 'synthesizer',
          'agent_type': 'synthesizer',
          'parent_id': 'root-1',
          'status': 'completed',
        },
      ],
    });

    test('fromJson parses valid graph', () {
      final graph = makeGraph();
      expect(graph.investigationId, 'inv-1');
      expect(graph.mode, 'debate');
      expect(graph.debateRounds, 2);
      expect(graph.agents.length, 4);
    });

    test('fromJson computes totalToolCalls from agents when missing', () {
      final graph = CouncilActivityGraph.fromJson({
        'investigation_id': 'inv-1',
        'mode': 'standard',
        'started_at': 'now',
        'agents': [
          {
            'agent_id': 'a1', 'agent_name': 'panel', 'agent_type': 'panel',
            'tool_calls': [
              {'call_id': 'c1', 'tool_name': 't1'},
              {'call_id': 'c2', 'tool_name': 't2'},
            ],
          },
          {
            'agent_id': 'a2', 'agent_name': 'panel2', 'agent_type': 'panel',
            'tool_calls': [{'call_id': 'c3', 'tool_name': 't3'}],
          },
        ],
      });
      expect(graph.totalToolCalls, 3);
    });

    test('fromJson uses explicit totalToolCalls when present', () {
      final graph = CouncilActivityGraph.fromJson({
        'investigation_id': 'inv-1',
        'mode': 'standard',
        'started_at': 'now',
        'total_tool_calls': 10,
        'total_llm_calls': 5,
        'agents': [],
      });
      expect(graph.totalToolCalls, 10);
      expect(graph.totalLLMCalls, 5);
    });

    test('getAgentById finds existing agent', () {
      final graph = makeGraph();
      final agent = graph.getAgentById('panel-1');
      expect(agent, isNotNull);
      expect(agent!.agentName, 'trace_panel');
    });

    test('getAgentById returns null for missing agent', () {
      final graph = makeGraph();
      expect(graph.getAgentById('nonexistent'), isNull);
    });

    test('getChildren returns children of agent', () {
      final graph = makeGraph();
      final children = graph.getChildren('root-1');
      expect(children.length, 3);
    });

    test('rootAgents returns agents with no parent', () {
      final graph = makeGraph();
      expect(graph.rootAgents.length, 1);
      expect(graph.rootAgents[0].agentName, 'sre_agent');
    });

    test('panelAgents returns panel-type agents', () {
      final graph = makeGraph();
      expect(graph.panelAgents.length, 1);
    });

    test('criticAgent returns the critic', () {
      final graph = makeGraph();
      expect(graph.criticAgent, isNotNull);
      expect(graph.criticAgent!.agentName, 'critic');
    });

    test('synthesizerAgent returns the synthesizer', () {
      final graph = makeGraph();
      expect(graph.synthesizerAgent, isNotNull);
      expect(graph.synthesizerAgent!.agentName, 'synthesizer');
    });

    test('criticAgent returns null when no critic', () {
      final graph = CouncilActivityGraph(
        investigationId: 'inv', mode: 'fast', startedAt: 'now',
      );
      expect(graph.criticAgent, isNull);
    });

    test('allToolCallsSorted returns sorted tool calls', () {
      final graph = makeGraph();
      final calls = graph.allToolCallsSorted;
      expect(calls.length, 2);
    });

    test('toolCallsByDashboardCategory groups correctly', () {
      final graph = makeGraph();
      final grouped = graph.toolCallsByDashboardCategory;
      expect(grouped['traces']!.length, 2);
    });

    test('fromJson provides defaults', () {
      final graph = CouncilActivityGraph.fromJson(const {});
      expect(graph.investigationId, '');
      expect(graph.mode, 'standard');
      expect(graph.agents, isEmpty);
      expect(graph.debateRounds, 1);
    });
  });

  // ===========================================================================
  // CouncilSynthesisData
  // ===========================================================================
  group('CouncilSynthesisData', () {
    test('fromJson parses valid data', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'Database connection pool exhaustion.',
        'overall_severity': 'critical',
        'overall_confidence': 0.92,
        'mode': 'debate',
        'rounds': 3,
        'panels': [
          {'panel': 'trace', 'summary': 'High latency', 'severity': 'warning', 'confidence': 0.8},
          {'panel': 'logs', 'summary': 'Error spike', 'severity': 'critical', 'confidence': 0.95},
        ],
        'critic_report': {
          'agreements': ['DB issue confirmed'],
          'contradictions': [],
          'gaps': [],
          'revised_confidence': 0.92,
        },
      });
      expect(data.synthesis, 'Database connection pool exhaustion.');
      expect(data.overallSeverity, 'critical');
      expect(data.overallConfidence, 0.92);
      expect(data.mode, 'debate');
      expect(data.rounds, 3);
      expect(data.panels.length, 2);
      expect(data.criticReport, isNotNull);
      expect(data.isDebateMode, isTrue);
      expect(data.hasCriticReport, isTrue);
    });

    test('fromJson provides defaults', () {
      final data = CouncilSynthesisData.fromJson(const {});
      expect(data.synthesis, '');
      expect(data.overallSeverity, 'info');
      expect(data.overallConfidence, 0.0);
      expect(data.mode, 'standard');
      expect(data.rounds, 1);
      expect(data.panels, isEmpty);
      expect(data.criticReport, isNull);
      expect(data.activityGraph, isNull);
    });

    test('fromJson unwraps nested result key', () {
      final data = CouncilSynthesisData.fromJson({
        'result': {
          'synthesis': 'Nested synthesis',
          'overall_severity': 'warning',
          'overall_confidence': 0.7,
          'panels': [],
        },
      });
      expect(data.synthesis, 'Nested synthesis');
      expect(data.overallSeverity, 'warning');
    });

    test('getPanelByType finds matching panel', () {
      final data = CouncilSynthesisData(
        synthesis: 'test', overallSeverity: 'info', overallConfidence: 0.5,
        mode: 'standard', rounds: 1, rawData: const {},
        panels: [
          PanelFinding(panel: 'trace', summary: 's', severity: 'info', confidence: 0.5, evidence: [], recommendedActions: []),
          PanelFinding(panel: 'logs', summary: 's', severity: 'info', confidence: 0.5, evidence: [], recommendedActions: []),
        ],
      );
      expect(data.getPanelByType('trace'), isNotNull);
      expect(data.getPanelByType('TRACE'), isNotNull);
      expect(data.getPanelByType('nonexistent'), isNull);
    });

    test('isDebateMode detects debate', () {
      final debate = CouncilSynthesisData(
        synthesis: '', overallSeverity: '', overallConfidence: 0,
        mode: 'debate', rounds: 1, panels: [], rawData: const {},
      );
      final standard = CouncilSynthesisData(
        synthesis: '', overallSeverity: '', overallConfidence: 0,
        mode: 'standard', rounds: 1, panels: [], rawData: const {},
      );
      expect(debate.isDebateMode, isTrue);
      expect(standard.isDebateMode, isFalse);
    });

    test('totalToolCalls and totalLLMCalls from activityGraph', () {
      final data = CouncilSynthesisData(
        synthesis: '', overallSeverity: '', overallConfidence: 0,
        mode: 'standard', rounds: 1, panels: [], rawData: const {},
        activityGraph: CouncilActivityGraph(
          investigationId: 'inv-1', mode: 'standard', startedAt: 'now',
          totalToolCalls: 10, totalLLMCalls: 5,
        ),
      );
      expect(data.totalToolCalls, 10);
      expect(data.totalLLMCalls, 5);
    });

    test('totalToolCalls returns 0 when no activityGraph', () {
      final data = CouncilSynthesisData(
        synthesis: '', overallSeverity: '', overallConfidence: 0,
        mode: 'standard', rounds: 1, panels: [], rawData: const {},
      );
      expect(data.totalToolCalls, 0);
      expect(data.totalLLMCalls, 0);
    });
  });

  // ===========================================================================
  // VegaChartData
  // ===========================================================================
  group('VegaChartData', () {
    test('hasCharts is true when charts exist', () {
      final data = VegaChartData(
        question: 'q', answer: 'a',
        vegaLiteCharts: [{'mark': 'bar'}],
      );
      expect(data.hasCharts, isTrue);
    });

    test('hasCharts is false when empty', () {
      final data = VegaChartData(question: 'q', answer: 'a');
      expect(data.hasCharts, isFalse);
    });
  });
}
