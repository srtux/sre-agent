import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import type { RegistryAgent, AgentRegistryResponse } from '../types';

interface AgentContextType {
  projectId: string;
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
  const [loadingAgents, setLoadingAgents] = useState<boolean>(true);
  const [errorAgents, setErrorAgents] = useState<string | null>(null);

  const queryClient = useQueryClient();

  const { data: agentsData, isLoading, error } = useQuery({
    queryKey: ['agents', projectId, 720],
    queryFn: async () => {
      const res = await axios.get<AgentRegistryResponse>('/api/v1/graph/registry/agents', {
        params: { project_id: projectId, hours: 720 }
      });
      return res.data;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  useEffect(() => {
    if (agentsData?.agents && agentsData.agents.length > 0) {
      setAvailableAgents(agentsData.agents);

      setServiceName(prevServiceName => {
        const currentExists = agentsData.agents.some(a => a.serviceName === prevServiceName);
        if (!currentExists) {
          const highestVolumeAgent = agentsData.agents.reduce((prev, current) =>
            (prev.totalSessions > current.totalSessions) ? prev : current
          );
          const defaultName = highestVolumeAgent.serviceName;
          localStorage.setItem('agent_graph_service_name', defaultName);
          return defaultName;
        }
        return prevServiceName;
      });
    } else {
      setAvailableAgents([]);
    }
  }, [agentsData]);

  useEffect(() => {
    setLoadingAgents(isLoading);
  }, [isLoading]);

  useEffect(() => {
    if (error) {
      setErrorAgents(`Failed to load agents: ${error.message}`);
    } else {
      setErrorAgents(null);
    }
  }, [error]);

  useEffect(() => {
    if (!projectId) return;

    // Prefetch tools and topology for the current UI state to speed up initial view switch
    queryClient.prefetchQuery({
      queryKey: ['tools', projectId, 720],
      queryFn: async () => {
        const res = await axios.get('/api/v1/graph/registry/tools', { params: { project_id: projectId, hours: 720 } });
        return res.data;
      },
      staleTime: 5 * 60 * 1000,
    });

    queryClient.prefetchQuery({
      queryKey: ['topology', projectId, 720],
      queryFn: async () => {
        const res = await axios.get('/api/v1/graph/topology', { params: { project_id: projectId, hours: 720 } });
        return res.data;
      },
      staleTime: 5 * 60 * 1000,
    });
  }, [projectId, queryClient]);

  // Sync to local storage when changed
  useEffect(() => {
    localStorage.setItem('agent_graph_service_name', serviceName);
  }, [serviceName]);

  return (
    <AgentContext.Provider
      value={{
        projectId,
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
