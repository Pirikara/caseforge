import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';
import { TestStep } from './useTestCases';

export interface TestStepDetail extends TestStep {
  name?: string;
  request_headers?: Record<string, string>;
  request_params?: Record<string, string>;
  extract_rules?: Record<string, string>;
  path_params?: Record<string, string>;
  query_params?: Record<string, string>;
}


// テストステップ詳細を取得するフック
export function useTestStepDetail(serviceId: string, caseId: string, stepId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestStepDetail>(
    serviceId && caseId && stepId ? `/api/services/${serviceId}/test-cases/${caseId}/steps/${stepId}` : null,
    fetcher
  );
  
  return { testStep: data, isLoading, error, mutate };
}

// テストステップを更新するための関数
export async function updateTestStep(serviceId: string, caseId: string, stepId: string, data: any) {
  return await fetcher(`/api/services/${serviceId}/test-cases/${caseId}/steps/${stepId}`, 'PUT', data);
}

// テストケースに属するテストステップ一覧を取得するフック
export function useTestSteps(serviceId: string, caseId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestStepDetail[]>(
    serviceId && caseId ? `/api/services/${serviceId}/test-cases/${caseId}/test-steps` : null,
    fetcher
  );
  
  return { testSteps: data, isLoading, error, mutate };
}

// テストステップを作成するための関数
export async function createTestStep(serviceId: string, caseId: string, data: any) {
  return await fetcher(`/api/services/${serviceId}/test-cases/${caseId}/test-steps`, 'POST', data);
}

// テストステップを削除するための関数
export async function deleteTestStep(serviceId: string, caseId: string, stepId: string) {
  return await fetcher(`/api/services/${serviceId}/test-cases/${caseId}/steps/${stepId}`, 'DELETE');
}
