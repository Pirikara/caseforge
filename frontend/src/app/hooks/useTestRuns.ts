import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface TestRun {
  id: string;
  run_id: string;
  project_id: string;
  status: 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  results?: TestResult[];
}

export interface TestResult {
  id: string;
  test_run_id: string;
  test_case_id: string;
  status_code: number;
  passed: boolean;
  response_time: number;
  error_message?: string;
  response_body?: any;
}

export function useTestRuns(projectId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestRun[]>(
    projectId ? `/api/projects/${projectId}/runs` : null,
    fetcher
  );
  
  return {
    testRuns: data,
    isLoading,
    error,
    mutate,
  };
}