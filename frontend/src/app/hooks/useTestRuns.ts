import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface TestRun {
  id: string;
  run_id: string;
  suite_id: string;
  project_id: string;
  status: 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  test_case_results?: TestCaseResult[];
}

export interface TestCaseResult {
  id: string;
  test_run_id: string;
  case_id: string;
  status: 'passed' | 'failed' | 'skipped';
  error_message?: string;
  step_results?: StepResult[];
}

export interface StepResult {
  id: string;
  test_case_result_id: string;
  step_id: string;
  sequence: number;
  method: string;
  path: string;
  status_code?: number;
  passed: boolean;
  response_time?: number;
  error_message?: string;
  response_body?: any;
  extracted_values?: Record<string, any>;
}

export interface TestStep {
  id: string;
  case_id: string;
  sequence: number;
  name?: string;
  method: string;
  path: string;
  request_headers?: Record<string, any>;
  request_body?: any;
  request_params?: Record<string, any>;
  expected_status?: number;
  extract_rules?: Record<string, string>;
}

export interface TestCase {
  id: string;
  suite_id: string;
  name: string;
  description?: string;
  error_type?: string;
  target_method: string;
  target_path: string;
  test_steps?: TestStep[];
}

export interface TestSuite {
  id: string;
  project_id: string;
  target_method: string;
  target_path: string;
  name: string;
  description?: string;
  test_cases?: TestCase[];
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

export function useTestRunDetail(projectId: string, runId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<TestRun>(
    projectId && runId ? `/api/projects/${projectId}/runs/${runId}` : null,
    fetcher
  );

  return {
    testRun: data,
    isLoading,
    error,
    mutate,
  };
}