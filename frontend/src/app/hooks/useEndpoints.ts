import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

export interface Endpoint {
  id: string;
  path: string;
  method: string;
  summary?: string;
  description?: string;
  request_body?: any;
  request_headers?: Record<string, any>;
  request_query_params?: Record<string, any>;
  responses?: Record<string, any>;
}

export function useEndpoints(serviceId: number) {
  const { data, error, isLoading, mutate } = useSWR<Endpoint[]>(
    `/api/services/${serviceId.toString()}/endpoints`,
    async (url: string) => {
      const response = await fetch(`${API}${url}`);
      
      if (!response.ok) throw new Error(`API ${response.status}`);
      
      const jsonData = await response.json();      
      return jsonData;
    }
  );

  return {
    endpoints: data,
    isLoading,
    isError: error,
    mutate
  };
}
