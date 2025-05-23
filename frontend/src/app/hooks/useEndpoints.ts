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
      
      console.log('Endpoints API response:', {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries([...response.headers.entries()])
      });
      
      if (!response.ok) throw new Error(`API ${response.status}`);
      
      const jsonData = await response.json();
      
      if (jsonData && jsonData.length > 0) {
        const firstEndpoint = jsonData[0];
        console.log('First endpoint structure:', {
          keys: Object.keys(firstEndpoint),
          id: firstEndpoint.id,
          path: firstEndpoint.path,
          method: firstEndpoint.method,
          request_body: firstEndpoint.request_body !== undefined ? 'あり' : 'なし',
          request_body_type: firstEndpoint.request_body !== undefined ? typeof firstEndpoint.request_body : 'undefined',
          request_body_value: firstEndpoint.request_body !== undefined ?
            JSON.stringify(firstEndpoint.request_body).substring(0, 100) + '...' : 'undefined',
          request_headers: firstEndpoint.request_headers !== undefined ? 'あり' : 'なし',
          request_headers_type: firstEndpoint.request_headers !== undefined ? typeof firstEndpoint.request_headers : 'undefined',
          request_headers_keys: firstEndpoint.request_headers !== undefined ?
            Object.keys(firstEndpoint.request_headers).length : 'undefined',
          request_query_params: firstEndpoint.request_query_params !== undefined ? 'あり' : 'なし',
          request_query_params_type: firstEndpoint.request_query_params !== undefined ?
            typeof firstEndpoint.request_query_params : 'undefined',
          request_query_params_keys: firstEndpoint.request_query_params !== undefined ?
            Object.keys(firstEndpoint.request_query_params).length : 'undefined',
          responses: firstEndpoint.responses !== undefined ? 'あり' : 'なし',
          responses_type: firstEndpoint.responses !== undefined ? typeof firstEndpoint.responses : 'undefined',
          responses_keys: firstEndpoint.responses !== undefined ?
            Object.keys(firstEndpoint.responses).length : 'undefined'
        });
      }
      
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
