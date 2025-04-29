import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface TestChainStep {
  id?: string;
  sequence: number;
  name?: string;
  method: string;
  path: string;
  request?: {
    headers?: Record<string, string>;
    body?: any;
    params?: Record<string, string>;
  };
  request_headers?: Record<string, string>; // 後方互換性のため残す
  request_body?: any; // 後方互換性のため残す
  request_params?: Record<string, string>; // 後方互換性のため残す
  expected_status?: number;
  extract_rules?: Record<string, string>;
}

export interface TestChain {
  id: string;
  chain_id?: string;
  project_id?: string;
  name: string;
  description?: string;
  tags?: string[];
  steps?: TestChainStep[];
  steps_count?: number;
  created_at: string;
  updated_at?: string;
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

export function useTestChainDetail(projectId: string, chainId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<TestChain>(
    projectId && chainId ? `/api/projects/${projectId}/chains/${chainId}` : null,
    fetcher
  );
  
  return {
    testChain: data,
    isLoading,
    error,
    mutate,
  };
}