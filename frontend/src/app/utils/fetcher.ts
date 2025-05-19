const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

/**
 * 共通のfetcher関数
 * SWRで使用するためのfetcher関数です
 */
export const fetcher = async (url: string, method: string = 'GET', body?: any) => {
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API}${url}`, options);

  if (!response.ok) {
    const errorDetail = await response.text();
    throw new Error(`API Error: ${response.status} - ${errorDetail}`);
  }

  // DELETE リクエストなどでボディがない場合を考慮
  if (response.status === 204 || response.headers.get('Content-Length') === '0') {
    return null;
  }

  return response.json();
};

/**
 * サービスを更新する関数
 */
export const updateService = async (serviceId: string, data: any) => {
  return fetcher(`/api/services/${serviceId}`, 'PUT', data);
};
