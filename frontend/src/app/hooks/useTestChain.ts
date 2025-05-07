import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';
import { TestChain } from '@/hooks/useTestRuns'; // TestChain 型をインポート

export function useTestChain(projectId: string | undefined, chainId: string | undefined) {
  const { data, error, isLoading, mutate } = useSWR<TestChain>(
    (projectId && chainId) ? `/api/projects/${projectId}/chains/${chainId}` : null,
    fetcher
  );

  return {
    testChain: data,
    isLoading,
    error,
    mutate,
  };
}