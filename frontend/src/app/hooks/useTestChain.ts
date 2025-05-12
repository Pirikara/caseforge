import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

import { TestSuite } from '@/hooks/useTestRuns'; // TestSuite 型をインポート

export function useTestSuiteDetail(projectId: string | undefined, suiteId: string | undefined) {
  const { data, error, isLoading, mutate } = useSWR<TestSuite>(
    (projectId && suiteId) ? `/api/projects/${projectId}/test-suites/${suiteId}` : null,
    fetcher
  );

  return {
    testSuite: data,
    isLoading,
    error,
    mutate,
  };
}