import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface TestChainStep {
  id: string;
  sequence: number;
  name?: string;
  method: string;
  path: string;
  request_headers?: Record<string, string>;
  request_body?: any;
  request_params?: Record<string, string>;
  expected_status?: number;
  extract_rules?: Record<string, string>;
}

export interface TestChain {
  id: string;
  chain_id: string;
  project_id: string;
  name: string;
  description?: string;
  tags?: string[];
  steps: TestChainStep[];
  created_at: string;
  updated_at: string;
}

export function useTestChains(projectId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestChain[]>(
    projectId ? `/api/projects/${projectId}/chains` : null,
    fetcher
  );
  
  return {
    testChains: data,
    isLoading,
    error,
    mutate,
  };
}