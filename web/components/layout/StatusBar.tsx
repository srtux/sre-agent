"use client";

import React from "react";
import { format } from "date-fns";
import {
  Activity,
  Bot,
  Brain,
  ChartLine,
  CircleDot,
  Clock,
  FileSearch,
  Loader2,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useBackendStatus } from "@/lib/useBackendStatus";
import type { AgentStatus, AgentType } from "@/types/adk-schema";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ProjectSelector } from "./ProjectSelector";

interface StatusBarProps {
  agentStatus: AgentStatus;
  currentProjectId: string;
  onProjectChange: (projectId: string) => void;
  className?: string;
}

// Agent configurations
const agentConfig: Record<
  AgentType,
  {
    name: string;
    icon: typeof Bot;
    color: string;
    bgColor: string;
  }
> = {
  orchestrator: {
    name: "Orchestrator",
    icon: Brain,
    color: "text-purple-400",
    bgColor: "bg-purple-500/10",
  },
  latency_specialist: {
    name: "Latency Specialist",
    icon: Activity,
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
  },
  error_analyst: {
    name: "Error Analyst",
    icon: Shield,
    color: "text-red-400",
    bgColor: "bg-red-500/10",
  },
  log_pattern_engine: {
    name: "Drain3 Engine",
    icon: FileSearch,
    color: "text-green-400",
    bgColor: "bg-green-500/10",
  },
  metrics_correlator: {
    name: "Metrics Correlator",
    icon: ChartLine,
    color: "text-yellow-400",
    bgColor: "bg-yellow-500/10",
  },
  remediation_advisor: {
    name: "Remediation Advisor",
    icon: Zap,
    color: "text-orange-400",
    bgColor: "bg-orange-500/10",
  },
  idle: {
    name: "Ready",
    icon: CircleDot,
    color: "text-muted-foreground",
    bgColor: "bg-muted",
  },
};

export function StatusBar({
  agentStatus,
  currentProjectId,
  onProjectChange,
  className,
}: StatusBarProps) {
  const config = agentConfig[agentStatus.currentAgent];
  const Icon = config.icon;
  const isActive = agentStatus.currentAgent !== "idle";
  const backendStatus = useBackendStatus();

  // Calculate elapsed time
  const elapsedTime = agentStatus.startTime
    ? Math.floor(
      (Date.now() - new Date(agentStatus.startTime).getTime()) / 1000
    )
    : 0;

  return (
    <TooltipProvider>
      <div
        className={cn(
          "flex items-center justify-between px-6 h-12 border-b border-border bg-card/80 backdrop-blur-md sticky top-0 z-30",
          className
        )}
      >
        {/* Left side - Agent status */}
        <div className="flex items-center gap-4">
          {/* Agent indicator */}
          <div
            className={cn(
              "flex items-center gap-2.5 px-3 py-1.5 rounded-full border border-border/50",
              config.bgColor,
              isActive && "shadow-[0_0_15px_-3px_rgba(59,130,246,0.3)] border-primary/20"
            )}
          >
            {isActive ? (
              <Loader2 className={cn("h-4 w-4 animate-spin", config.color)} />
            ) : (
              <Icon className={cn("h-4 w-4", config.color)} />
            )}
            <span className={cn("text-xs font-semibold tracking-wide uppercase", config.color)}>
              {config.name}
            </span>
          </div>

          {/* Status message */}
          <span className="text-xs font-medium text-foreground/80 max-w-[400px] truncate">
            {agentStatus.message === config.name || agentStatus.currentAgent === "idle"
              ? "System standby"
              : agentStatus.message}
          </span>

          {/* Progress indicator */}
          {agentStatus.progress !== undefined && agentStatus.progress > 0 && (
            <div className="flex items-center gap-3 ml-2 border-l border-border/50 pl-4">
              <div className="w-24 h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-500 ease-out"
                  style={{ width: `${agentStatus.progress}%` }}
                />
              </div>
              <span className="text-[10px] text-muted-foreground font-mono">
                {agentStatus.progress}%
              </span>
            </div>
          )}

          {/* Elapsed time */}
          {isActive && agentStatus.startTime && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground px-2 py-0.5 rounded bg-muted/30">
                  <Clock className="h-3 w-3" />
                  <span className="font-mono">{elapsedTime}s</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                Started at{" "}
                {format(new Date(agentStatus.startTime), "HH:mm:ss")}
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* Right side - System info */}
        <div className="flex items-center gap-6 text-xs text-muted-foreground">
          {/* Project Selector */}
          <ProjectSelector
            currentProjectId={currentProjectId}
            onProjectChange={onProjectChange}
          />

          <div className="h-5 w-px bg-border/60" />

          {/* Council of Experts badge */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-2 px-2 py-1 rounded-md hover:bg-muted/50 transition-colors cursor-default">
                <Sparkles className="h-4 w-4 text-primary" />
                <span className="font-medium">Council of Experts</span>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              Multi-agent SRE system with specialized sub-agents
            </TooltipContent>
          </Tooltip>

          {/* Divider */}
          <div className="h-5 w-px bg-border/60" />

          {/* Connection status - Dynamic */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-2 cursor-help px-2 py-1 rounded-md hover:bg-muted/50 transition-colors">
                <div
                  className={cn(
                    "h-2 w-2 rounded-full",
                    backendStatus.status === "connected" && "bg-green-500 status-indicator",
                    backendStatus.status === "disconnected" && "bg-red-500",
                    backendStatus.status === "checking" && "bg-yellow-500 animate-pulse"
                  )}
                />
                <span className="font-medium">
                  {backendStatus.status === "connected" && "Connected"}
                  {backendStatus.status === "disconnected" && "Disconnected"}
                  {backendStatus.status === "checking" && "Checking..."}
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-xs">
              <div className="space-y-1">
                <p className="font-medium">Backend: {backendStatus.backendUrl || "localhost:8000"}</p>
                {backendStatus.lastChecked && (
                  <p className="text-xs text-muted-foreground">
                    Last checked: {format(backendStatus.lastChecked, "HH:mm:ss")}
                  </p>
                )}
                {backendStatus.error && (
                  <p className="text-xs text-red-400">{backendStatus.error}</p>
                )}
              </div>
            </TooltipContent>
          </Tooltip>

          {/* Current time */}
          <div className="font-mono bg-muted/30 px-2 py-0.5 rounded text-foreground/70">
            <ClockDisplay />
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}

// Separate component for client-side only clock to avoid hydration errors
function ClockDisplay() {
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return <>{format(new Date(), "HH:mm:ss")}</>;
}

export default StatusBar;
