"use client";

import React from "react";
import {
  Activity,
  AlertCircle,
  FileSearch,
  GitCompare,
  Layers,
  Shield,
  Zap,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { CanvasView } from "@/types/adk-schema";
import { TraceWaterfall } from "@/components/sre-widgets/TraceWaterfall";
import { LogPatternViewer } from "@/components/sre-widgets/LogPatternViewer";
import { MetricCorrelationChart } from "@/components/sre-widgets/MetricCorrelationChart";
import { RemediationPlan } from "@/components/sre-widgets/RemediationPlan";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface CanvasProps {
  view: CanvasView;
  onExecuteRemediation?: (action: any) => void;
  onActionClick?: (prompt: string) => void;
  className?: string;
}

// Empty state component
function EmptyState({ onActionClick }: { onActionClick?: (prompt: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[500px] text-center p-8 animate-in fade-in duration-1000">
      {/* Central Decorative Hub */}
      <div className="relative mb-12">
        {/* Animated Glow Rings */}
        <div className="absolute inset-0 scale-[2.5] bg-primary/5 rounded-full blur-3xl animate-pulse" />
        <div className="absolute inset-0 scale-[1.5] bg-blue-500/10 rounded-full blur-2xl animate-pulse delay-700" />

        {/* Central Icon container */}
        <div className="relative w-32 h-32 rounded-3xl bg-gradient-to-br from-card to-background border border-border/50 flex items-center justify-center shadow-2xl shadow-primary/20 backdrop-blur-xl">
          <Layers className="h-12 w-12 text-primary animate-pulse" />

          {/* Orbiting indicators */}
          <div className="absolute -top-1 -right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-4 w-4 bg-blue-500"></span>
          </div>
        </div>
      </div>

      <div className="max-w-2xl space-y-6">
        <div className="space-y-2">
          <h2 className="text-4xl font-bold tracking-tighter sm:text-5xl bg-clip-text text-transparent bg-gradient-to-b from-foreground to-foreground/50">
            SITUATION ROOM
          </h2>
          <p className="text-muted-foreground text-lg font-medium tracking-tight">
            Advanced SRE Observability & Remediation Engine
          </p>
        </div>

        <p className="text-muted-foreground/80 leading-relaxed max-w-lg mx-auto">
          System is on standby. Initiate an investigation by describing an incident
          or asking for specific analysis metrics.
        </p>

        <div className="pt-8 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
          {[
            {
              icon: Activity,
              label: "Trace Analysis",
              color: "text-blue-400",
              bg: "bg-blue-400/10",
              prompt: "Let's analyze a trace. Can you find some interesting traces for me or I can provide a trace ID?"
            },
            {
              icon: FileSearch,
              label: "Log Patterns",
              color: "text-emerald-400",
              bg: "bg-emerald-400/10",
              prompt: "Show me log patterns from the last hour for our services."
            },
            {
              icon: AlertCircle,
              label: "Anomaly Detection",
              color: "text-amber-400",
              bg: "bg-amber-400/10",
              prompt: "Are there any anomalies in our p99 latency metrics currently?"
            },
            {
              icon: Zap,
              label: "Root Cause",
              color: "text-orange-400",
              bg: "bg-orange-400/10",
              prompt: "Run a causal analysis to find the root cause of the latest latency spike."
            }
          ].map((item, i) => (
            <button
              key={i}
              onClick={() => onActionClick?.(item.prompt)}
              className={cn(
                "group flex flex-col items-center gap-3 p-4 rounded-2xl border border-border/40 transition-all duration-300",
                "bg-card/40 backdrop-blur-sm shadow-lg hover:shadow-primary/10 hover:border-primary/50 hover:bg-primary/5 hover:-translate-y-1 active:scale-95"
              )}
            >
              <div className={cn("p-2.5 rounded-xl transition-all duration-300 group-hover:scale-110", item.bg, "group-hover:bg-primary/20")}>
                <item.icon className={cn("h-5 w-5", item.color)} />
              </div>
              <span className="text-[10px] font-bold tracking-widest uppercase opacity-60 group-hover:opacity-100 transition-opacity">
                {item.label}
              </span>
            </button>
          ))}
        </div>

        {/* Status indicator footer */}
        <div className="flex items-center justify-center gap-2 pt-12 text-[10px] font-mono text-muted-foreground/50 uppercase tracking-[0.2em]">
          <span className="flex h-1.5 w-1.5 rounded-full bg-green-500/50"></span>
          All systems operational
          <span className="mx-2">•</span>
          Intelligence core active
        </div>
      </div>
    </div>
  );
}

// Trace comparison view
function TraceComparisonView({ data }: { data: any }) {
  return (
    <div className="space-y-4">
      <Card className="bg-card border-border">
        <CardHeader className="py-3 px-4 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GitCompare className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm font-medium">
                Trace Comparison
              </CardTitle>
            </div>
            <Badge
              variant={
                data.overall_assessment === "healthy"
                  ? "success"
                  : data.overall_assessment === "degraded"
                    ? "warning"
                    : "error"
              }
            >
              {data.overall_assessment.toUpperCase()}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-4">
          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="text-xs text-muted-foreground mb-1">Baseline</p>
              <p className="text-sm font-mono">
                {data.baseline_summary.total_duration_ms.toFixed(1)}ms
              </p>
              <p className="text-xs text-muted-foreground">
                {data.baseline_summary.span_count} spans
              </p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="text-xs text-muted-foreground mb-1">Target</p>
              <p className="text-sm font-mono text-red-400">
                {data.target_summary.total_duration_ms.toFixed(1)}ms
              </p>
              <p className="text-xs text-muted-foreground">
                {data.target_summary.error_count} errors
              </p>
            </div>
          </div>

          {/* Root cause hypothesis */}
          <div className="p-3 rounded-lg bg-red-900/20 border border-red-900/50 mb-4">
            <p className="text-xs text-red-400 font-medium mb-1">
              Root Cause Hypothesis
            </p>
            <p className="text-sm text-foreground">
              {data.root_cause_hypothesis}
            </p>
          </div>

          {/* Latency findings */}
          {data.latency_findings.length > 0 && (
            <div>
              <p className="text-xs text-muted-foreground mb-2">
                Latency Regressions
              </p>
              <div className="space-y-2">
                {data.latency_findings.slice(0, 5).map((finding: any, idx: number) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded bg-muted/30 text-xs"
                  >
                    <span className="font-mono">{finding.span_name}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-muted-foreground">
                        {finding.baseline_ms.toFixed(1)}ms →{" "}
                        <span className="text-red-400">
                          {finding.target_ms.toFixed(1)}ms
                        </span>
                      </span>
                      <Badge variant="error">
                        +{finding.diff_percent.toFixed(0)}%
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Causal analysis view
function CausalAnalysisView({ data }: { data: any }) {
  return (
    <Card className="bg-card border-border">
      <CardHeader className="py-3 px-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm font-medium">
              Causal Analysis
            </CardTitle>
          </div>
          <Badge
            variant={
              data.confidence === "high"
                ? "success"
                : data.confidence === "medium"
                  ? "warning"
                  : "error"
            }
          >
            {data.confidence.toUpperCase()} CONFIDENCE
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-4">
        {/* Primary root cause */}
        <div className="p-3 rounded-lg bg-red-900/20 border border-red-900/50 mb-4">
          <p className="text-xs text-red-400 font-medium mb-1">
            Primary Root Cause
          </p>
          <p className="text-sm text-foreground font-medium">
            {data.primary_root_cause}
          </p>
        </div>

        {/* Causal chain visualization */}
        <div className="mb-4">
          <p className="text-xs text-muted-foreground mb-2">Causal Chain</p>
          <div className="flex items-center gap-2 overflow-x-auto py-2">
            {data.causal_chain.map((link: any, idx: number) => (
              <React.Fragment key={idx}>
                <div
                  className={cn(
                    "px-3 py-2 rounded text-xs font-mono whitespace-nowrap",
                    link.effect_type === "root_cause"
                      ? "bg-red-500/20 border border-red-500/50 text-red-400"
                      : link.effect_type === "direct_effect"
                        ? "bg-orange-500/20 border border-orange-500/50 text-orange-400"
                        : "bg-yellow-500/20 border border-yellow-500/50 text-yellow-400"
                  )}
                >
                  {link.span_name}
                  <span className="block text-[10px] opacity-75">
                    +{link.latency_contribution_ms.toFixed(0)}ms
                  </span>
                </div>
                {idx < data.causal_chain.length - 1 && (
                  <span className="text-muted-foreground">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Conclusion */}
        <div className="p-3 rounded-lg bg-muted/50">
          <p className="text-xs text-muted-foreground mb-1">Conclusion</p>
          <p className="text-sm">{data.conclusion}</p>
        </div>

        {/* Recommended actions */}
        {data.recommended_actions.length > 0 && (
          <div className="mt-4">
            <p className="text-xs text-muted-foreground mb-2">
              Recommended Actions
            </p>
            <ul className="space-y-1">
              {data.recommended_actions.map((action: string, idx: number) => (
                <li key={idx} className="text-xs flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function Canvas({ view, onExecuteRemediation, onActionClick, className }: CanvasProps) {
  const renderContent = () => {
    switch (view.type) {
      case "empty":
        return <EmptyState onActionClick={onActionClick} />;

      case "trace":
        return <TraceWaterfall trace={view.data} />;

      case "trace_comparison":
        return <TraceComparisonView data={view.data} />;

      case "log_patterns":
        return <LogPatternViewer data={view.data} />;

      case "metrics":
        return <MetricCorrelationChart data={view.data} />;

      case "remediation":
        return (
          <RemediationPlan
            data={view.data}
            onExecute={onExecuteRemediation}
          />
        );

      case "causal_analysis":
        return <CausalAnalysisView data={view.data} />;

      default:
        return <EmptyState />;
    }
  };

  return (
    <div className={cn("h-full overflow-hidden bg-background", className)}>
      <ScrollArea className="h-full">
        <div className="p-4">{renderContent()}</div>
      </ScrollArea>
    </div>
  );
}

export default Canvas;
