import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import type { RegistryAgent, AgentRegistryResponse } from '../types';

interface AgentContextType {
  serviceName: string;
  setServiceName: (name: string) => void;
  availableAgents: RegistryAgent[];
  loadingAgents: boolean;
  errorAgents: string | null;
}

const AgentContext = createContext<AgentContextType | undefined>(undefined);

export function AgentProvider({ children, projectId }: { children: ReactNode, projectId: string }) {
  const [serviceName, setServiceName] = useState<string>(localStorage.getItem('agent_graph_service_name') || 'sre-agent');
  const [availableAgents, setAvailableAgents] = useState<RegistryAgent[]>([]);
  const [loadingAgents, setLoadingAgents] = useState<boolean>(false);
  const [errorAgents, setErrorAgents] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;

    let isMounted = true;
    setLoadingAgents(true);

    // Fetch available agents
    axios.get<AgentRegistryResponse>('/api/v1/registry/agents', { params: { project_id: projectId, hours: 24 } })
      .then(res => {
        if (!isMounted) return;
        const agents = res.data.agents || [];
        setAvailableAgents(agents);

        // Auto-select highest volume agent if the currently cached one doesn't exist
        // or we just want to default to the highest volume one if none is selected
        if (agents.length > 0) {
          setServiceName(prevServiceName => {
            const currentExists = agents.some(a => a.serviceName === prevServiceName);
            if (!currentExists) {
              const highestVolumeAgent = agents.reduce((prev, current) =>
                (prev.totalSessions > current.totalSessions) ? prev : current
              );
              const defaultName = highestVolumeAgent.serviceName;
              localStorage.setItem('agent_graph_service_name', defaultName);
              return defaultName;
            }
            return prevServiceName;
          });
        }
      })
      .catch(err => {
        if (!isMounted) return;
        setErrorAgents(`Failed to load agents: ${err.message}`);
      })
      .finally(() => {
        if (isMounted) setLoadingAgents(false);
      });

    return () => {
      isMounted = false;
    };
  }, [projectId]);

  // Sync to local storage when changed
  useEffect(() => {
    localStorage.setItem('agent_graph_service_name', serviceName);
  }, [serviceName]);

  return (
    <AgentContext.Provider
      value={{
        serviceName,
        setServiceName,
        availableAgents,
        loadingAgents,
        errorAgents,
      }}
    >
      {children}
    </AgentContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAgentContext() {
  const context = useContext(AgentContext);
  if (context === undefined) {
    throw new Error('useAgentContext must be used within an AgentProvider');
  }
  return context;
}
