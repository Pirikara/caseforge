import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

import { TestSuite } from '@/hooks/useTestRuns'; // TestSuite 型をインポート

export function useTestSuiteDetail(serviceId: string | undefined, suiteId: string | undefined) {
  const { data, error, isLoading, mutate } = useSWR<TestSuite>(
    (serviceId && suiteId) ? `/api/services/${serviceId}/test-suites/${suiteId}` : null,
    fetcher
  );

  return {
    testSuite: data,
    isLoading,
    error,
    mutate,
  };
}
