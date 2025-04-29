import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

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

export function useEndpoints(projectId: string) {
  const { data, error, isLoading, mutate } = useSWR<Endpoint[]>(
    `/api/projects/${projectId}/endpoints`,
    fetcher
  );

  // デバッグログを追加
  console.log('useEndpoints hook:', {
    projectId,
    data,
    error,
    isLoading
  });

  // 詳細なデータログ
  if (data && data.length > 0) {
    console.log('最初のエンドポイントの詳細データ:', {
      id: data[0].id,
      path: data[0].path,
      method: data[0].method,
      request_body: data[0].request_body ? 'あり' : 'なし',
      request_body_type: data[0].request_body ? typeof data[0].request_body : 'N/A',
      request_body_value: data[0].request_body ? JSON.stringify(data[0].request_body).substring(0, 100) + '...' : 'N/A',
      request_headers: data[0].request_headers ? 'あり' : 'なし',
      request_headers_type: data[0].request_headers ? typeof data[0].request_headers : 'N/A',
      request_headers_keys: data[0].request_headers ? Object.keys(data[0].request_headers) : 'N/A',
      request_query_params: data[0].request_query_params ? 'あり' : 'なし',
      request_query_params_type: data[0].request_query_params ? typeof data[0].request_query_params : 'N/A',
      request_query_params_keys: data[0].request_query_params ? Object.keys(data[0].request_query_params) : 'N/A',
      responses: data[0].responses ? 'あり' : 'なし',
      responses_type: data[0].responses ? typeof data[0].responses : 'N/A',
      responses_keys: data[0].responses ? Object.keys(data[0].responses) : 'N/A'
    });
  }

  return {
    endpoints: data,
    isLoading,
    isError: error,
    mutate
  };
}