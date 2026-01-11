/**
 * SRE Agent API Client
 *
 * Provides type-safe access to the Python backend tools.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_SRE_AGENT_API_URL || "";

export const sreClient = {
  /**
   * Fetch a trace by ID
   */
  async getTrace(traceId: string, projectId?: string) {
    const params = new URLSearchParams();
    if (projectId) params.append("project_id", projectId);
    const queryString = params.toString() ? `?${params.toString()}` : "";

    const response = await fetch(`${API_BASE_URL}/api/tools/trace/${traceId}${queryString}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch trace: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Run log pattern analysis
   */
  async analyzeLogs(params: {
    filter: string;
    baseline_start: string;
    baseline_end: string;
    comparison_start: string;
    comparison_end: string;
    project_id?: string;
  }) {
    const response = await fetch(`${API_BASE_URL}/api/tools/logs/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      throw new Error(`Failed to analyze logs: ${response.statusText}`);
    }
    return response.json();
  }
};
