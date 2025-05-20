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

export function useTestCases(serviceId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestCase[]>(
    serviceId ? `/api/services/${serviceId}/test-cases` : null,
    fetcher
  );
  
  const deleteChain = async (chainId: string) => {
    try {
      await fetcher(`/api/services/${serviceId}/test-cases/${chainId}`, 'DELETE');
      // 削除成功後、SWRのキャッシュを更新して再フェッチ
      mutate();
    } catch (err) {
      console.error(`Failed to delete chain ${chainId} for service ${serviceId}:`, err);
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

export interface TestStep {
  id: string;
  sequence: number;
  method: string;
  path: string;
  request_body?: any;
  expected_status: number;
  expected_response?: any;
  extracted_values?: any;
}

export interface TestCaseDetail extends TestCase {
  steps?: TestStep[]; // テストステップの配列を追加
}

export function useTestCaseDetail(serviceId: string, caseId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestCaseDetail>(
    serviceId && caseId ? `/api/services/${serviceId}/test-cases/${caseId}` : null,
    fetcher
  );
  return { testCase: data, isLoading, error, mutate };
}
