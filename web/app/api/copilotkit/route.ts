import {
  CopilotRuntime,
  GoogleGenerativeAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";
import { GoogleAuth } from "google-auth-library";

// Create the CopilotKit runtime
const agentUrl = process.env.SRE_AGENT_URL || "http://127.0.0.1:8000";

async function getRuntime() {
  let remoteEndpoints = [];

  // Check if we are connecting directly to Vertex AI Agent Engine
  if (agentUrl.includes("googleapis.com") && agentUrl.includes("reasoningEngines")) {
    console.log("🚀 Connecting directly to Vertex AI Agent Engine");

    try {
      const auth = new GoogleAuth({
        scopes: ['https://www.googleapis.com/auth/cloud-platform']
      });
      const client = await auth.getClient();
      const accessToken = await client.getAccessToken();

      remoteEndpoints = [
        {
          url: agentUrl,
          headers: {
            Authorization: `Bearer ${accessToken.token}`,
          }
        } as any
      ];
    } catch (error) {
      console.error("❌ Failed to get Google Auth Token:", error);
      // Fallback to no auth if local or error
      remoteEndpoints = [{ url: agentUrl }];
    }

  } else {
// Standard Gateway/Local mode
    const copilotKitEndpoint = agentUrl.includes("/copilotkit")
      ? agentUrl
      : `${agentUrl.replace(/\/$/, "")}/copilotkit`;

    remoteEndpoints = [
      {
        url: copilotKitEndpoint,
      },
    ];
  }

  return new CopilotRuntime({
    remoteEndpoints,
    actions: [
      // System prompt for the SRE agent
      {
        name: "systemPrompt",
        description: "SRE Agent system context",
        handler: async () => {
          return {
            systemPrompt: `You are an expert SRE (Site Reliability Engineering) AI assistant specialized in analyzing and troubleshooting Google Cloud Platform infrastructure.

You have access to several powerful analysis tools:

1. **analyzeTrace**: Analyze distributed traces for latency bottlenecks and errors. Use this when investigating slow requests or failures.

2. **analyzeLogPatterns**: Use the Drain3 algorithm to cluster and analyze log patterns. Helps identify recurring issues and anomalies.

3. **analyzeMetrics**: Analyze time-series metrics and detect anomalies. Correlates with incident windows.

4. **compareTraces**: Compare a baseline (good) trace with a target (problematic) trace to identify regressions.

5. **runCausalAnalysis**: Run multi-agent causal analysis to identify root causes. Uses the Council of Experts architecture.

6. **getRemediationPlan**: Generate actionable remediation suggestions based on findings.

7. **executeRemediation**: Execute a remediation action (requires confirmation).

When analyzing incidents:
1. Start by understanding the symptoms
2. Gather data using trace, log, and metric analysis
3. Use comparison and causal analysis to identify root causes
4. Provide clear, actionable remediation plans

Always explain your findings in clear, technical terms. Reference specific spans, log patterns, or metrics when available. Prioritize remediation actions by risk and effort.`,
          };
        },
      },
    ],
  });
}

// Handle POST requests
export const POST = async (req: NextRequest) => {
  const runtime = await getRuntime();

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter: new GoogleGenerativeAIAdapter({
      model: "gemini-2.5-pro",
      // Allow using either GOOGLE_API_KEY or GEMINI_API_KEY
      apiKey: process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY,
    }),
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
