import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

import { TestCase, TestStep } from './useTestRuns'; // TestCase, TestStep 型をインポート

export interface TestSuite {
  id: string;
  project_id?: string;
  target_method: string;
  target_path: string;
  name: string;
  description?: string;
  test_cases?: TestCase[]; // TestCase のリスト
  test_cases_count?: number; // test_cases_count に変更
  created_at: string;
  updated_at?: string;
}

export function useTestSuites(projectId: string) { // useTestChains を useTestSuites に変更
  const { data, error, isLoading, mutate } = useSWR<TestSuite[]>( // TestChain[] を TestSuite[] に変更
    projectId ? `/api/projects/${projectId}/test-suites` : null, // /chains を /test-suites に変更
    fetcher
  );
  
  const deleteTestSuite = async (suiteId: string) => { // deleteChain を deleteTestSuite に変更, chainId を suiteId に変更
    try {
      await fetcher(`/api/projects/${projectId}/test-suites/${suiteId}`, 'DELETE'); // /chains/${chainId} を /test-suites/${suiteId} に変更
      // 削除成功後、SWRのキャッシュを更新して再フェッチ
      mutate();
    } catch (err) {
      console.error(`Failed to delete test suite ${suiteId}:`, err); // test chain ${chainId} を test suite ${suiteId} に変更
      throw err; // エラーを呼び出し元に伝える
    }
  };

  return {
    testSuites: data, // testChains を testSuites に変更
    isLoading,
    error,
    mutate,
    deleteTestSuite, // deleteChain を deleteTestSuite に変更
  };
}

export function useTestSuiteDetail(projectId: string, suiteId: string | null) { // useTestChainDetail を useTestSuiteDetail に変更, chainId を suiteId に変更
  const { data, error, isLoading, mutate } = useSWR<TestSuite>( // TestChain を TestSuite に変更
    projectId && suiteId ? `/api/projects/${projectId}/test-suites/${suiteId}` : null, // chainId を suiteId に変更, /chains/${chainId} を /test-suites/${suiteId} に変更
    fetcher
  );
  
  return {
    testSuite: data, // testChain を testSuite に変更
    isLoading,
    error,
    mutate,
  };
}