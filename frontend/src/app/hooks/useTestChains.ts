import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

import { TestCase, TestStep } from './useTestRuns';

export interface TestSuite {
  id: string;
  service_id?: string;
  target_method: string;
  target_path: string;
  name: string;
  description?: string;
  test_cases?: TestCase[];
  test_cases_count?: number;
  created_at: string;
  updated_at?: string;
}

export function useTestSuites(serviceId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestSuite[]>(
    serviceId ? `/api/services/${serviceId}/test-suites` : null,
    fetcher
  );
  
  const deleteTestSuite = async (suiteId: string) => {
    try {
      await fetcher(`/api/services/${serviceId}/test-suites/${suiteId}`, 'DELETE');
      mutate();
    } catch (err) {
      console.error(`Failed to delete test suite ${suiteId}:`, err);
      throw err;
    }
  };

  return {
    testSuites: data,
    isLoading,
    error,
    mutate,
    deleteTestSuite,
  };
}

export function useTestSuiteDetail(serviceId: string, suiteId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<TestSuite>(
    serviceId && suiteId ? `/api/services/${serviceId}/test-suites/${suiteId}` : null,
    fetcher
  );
  
  return {
    testSuite: data,
    isLoading,
    error,
    mutate,
  };
}
