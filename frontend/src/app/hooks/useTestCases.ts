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
      mutate();
    } catch (err) {
      console.error(`Failed to delete chain ${chainId} for service ${serviceId}:`, err);
      throw err;
    }
  };

  return {
    testCases: data,
    isLoading,
    error,
    mutate,
    deleteChain,
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
  steps?: TestStep[];
}

export function useTestCaseDetail(serviceId: string, caseId: string) {
  const { data, error, isLoading, mutate } = useSWR<TestCaseDetail>(
    serviceId && caseId ? `/api/services/${serviceId}/test-cases/${caseId}` : null,
    fetcher
  );
  return { testCase: data, isLoading, error, mutate };
}
