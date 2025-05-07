import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface ChainRun {
  id: string;
  run_id: string;
  chain_id: string;
  project_id: string;
  status: 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  step_results?: StepResult[];
}

export interface StepResult {
  id: string;
  chain_run_id: string;
  step_id: string;
  sequence: number;
  status_code?: number;
  passed: boolean;
  response_time?: number;
  error_message?: string;
  response_body?: any;
  extracted_values?: Record<string, any>;
}

export interface TestChainStep {
  id: string;
  chain_id: string; // バックエンドはintだが、フロントエンドではstringとして扱う可能性
  sequence: number;
  name?: string;
  method: string;
  path: string;
  request_headers?: Record<string, any>;
  request_body?: any;
  request_params?: Record<string, any>;
  expected_status?: number;
  extract_rules?: Record<string, string>;
  // StepResult とのリレーションシップはここでは不要
}

export interface TestChain {
  id: string; // バックエンドはintだが、フロントエンドではstringとして扱う可能性
  chain_id: string;
  project_id: string; // バックエンドはintだが、フロントエンドではstringとして扱う可能性
  name: string;
  description?: string;
  tags?: string;
  steps?: TestChainStep[]; // TestChainStep のリスト
  // ChainRun とのリレーションシップはここでは不要
}

export function useChainRuns(projectId: string) {
  const { data, error, isLoading, mutate } = useSWR<ChainRun[]>(
    projectId ? `/api/projects/${projectId}/runs` : null,
    fetcher
  );
  
  return {
    chainRuns: data,
    isLoading,
    error,
    mutate,
  };
}

// 後方互換性のために残す（非推奨）
export function useTestRuns(projectId: string) {
  console.warn('useTestRuns は非推奨です。代わりに useChainRuns を使用してください。');
  const { chainRuns, isLoading, error, mutate } = useChainRuns(projectId);
  
  return {
    testRuns: chainRuns,
    isLoading,
    error,
    mutate,
  };
}