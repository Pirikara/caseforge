import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

import { TestSuite } from '@/hooks/useTestRuns';

export function useTestSuiteDetail(serviceId: number | undefined, suiteId: string | undefined) {
  const { data, error, isLoading, mutate } = useSWR<TestSuite>(
    (serviceId && suiteId) ? `/api/services/${serviceId.toString()}/test-suites/${suiteId}` : null,
    fetcher
  );

  return {
    testSuite: data,
    isLoading,
    error,
    mutate,
  };
}
