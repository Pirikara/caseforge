import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface TestCase {
  id: string;
  case_id: string;
  title: string;
  method: string;
  path: string;
  request_body?: any;
  expected_status: number;
  expected_response?: any;
  purpose: string;
}

export function useTestCases(projectId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestCase[]>(
    projectId ? `/api/projects/${projectId}/tests` : null,
    fetcher
  );
  
  return {
    testCases: data,
    isLoading,
    error,
    mutate,
  };
}