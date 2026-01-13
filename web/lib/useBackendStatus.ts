"use client";

import { useState, useEffect, useCallback } from "react";

export type ConnectionStatus = "connected" | "disconnected" | "checking";

export interface BackendStatus {
  status: ConnectionStatus;
  lastChecked: Date | null;
  backendUrl: string;
  error?: string;
}

// Backend URL from environment - this is the ADK agent backend
const BACKEND_URL = process.env.NEXT_PUBLIC_SRE_AGENT_API_URL || "http://127.0.0.1:8000";
const POLL_INTERVAL = 30000; // 30 seconds

/**
 * React hook to monitor backend ADK agent connectivity.
 * Polls the backend periodically and returns current connection status.
 */
export function useBackendStatus(): BackendStatus {
  const [status, setStatus] = useState<ConnectionStatus>("checking");
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [error, setError] = useState<string | undefined>();

  const checkConnection = useCallback(async () => {
    setStatus("checking");

    try {
      // Try to reach the FastAPI docs endpoint (always available on FastAPI backends)
      const response = await fetch(`${BACKEND_URL}/docs`, {
        method: "GET",
        cache: "no-store",
      });

      if (response.ok) {
        setStatus("connected");
        setError(undefined);
      } else {
        setStatus("disconnected");
        setError(`Server returned ${response.status}`);
      }
    } catch (err) {
      setStatus("disconnected");
      setError(err instanceof Error ? err.message : "Connection failed");
    }

    setLastChecked(new Date());
  }, []);

  useEffect(() => {
    // Initial check
    checkConnection();

    // Set up polling
    const interval = setInterval(checkConnection, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [checkConnection]);

  return {
    status,
    lastChecked,
    backendUrl: BACKEND_URL,
    error,
  };
}
