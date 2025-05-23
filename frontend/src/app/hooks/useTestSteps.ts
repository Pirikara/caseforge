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


export function useTestStepDetail(serviceId: number, caseId: string, stepId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestStepDetail>(
    serviceId && caseId && stepId ? `/api/services/${serviceId.toString()}/test-cases/${caseId}/steps/${stepId}` : null,
    fetcher
  );
  
  return { testStep: data, isLoading, error, mutate };
}

export async function updateTestStep(serviceId: number, caseId: string, stepId: string, data: any) {
  return await fetcher(`/api/services/${serviceId.toString()}/test-cases/${caseId}/steps/${stepId}`, 'PUT', data);
}

export function useTestSteps(serviceId: number, caseId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestStepDetail[]>(
    serviceId && caseId ? `/api/services/${serviceId.toString()}/test-cases/${caseId}/test-steps` : null,
    fetcher
  );
  
  return { testSteps: data, isLoading, error, mutate };
}

export async function createTestStep(serviceId: number, caseId: string, data: any) {
  return await fetcher(`/api/services/${serviceId.toString()}/test-cases/${caseId}/test-steps`, 'POST', data);
}

export async function deleteTestStep(serviceId: number, caseId: string, stepId: string) {
  return await fetcher(`/api/services/${serviceId.toString()}/test-cases/${caseId}/steps/${stepId}`, 'DELETE');
}
