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
  
  const deleteChain = async (chainId: string) => {
    try {
      await fetcher(`/api/projects/${projectId}/chains/${chainId}`, 'DELETE');
      // 削除成功後、SWRのキャッシュを更新して再フェッチ
      mutate();
    } catch (err) {
      console.error(`Failed to delete chain ${chainId} for project ${projectId}:`, err);
      throw err; // エラーを呼び出し元に伝える
    }
  };

  return {
    testCases: data,
    isLoading,
    error,
    mutate,
    deleteChain, // 削除関数を追加
  };
}