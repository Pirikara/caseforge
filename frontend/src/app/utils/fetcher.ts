/**
 * APIリクエストを行うための汎用的なfetcher関数
 */
export async function fetcher<T = any>(
  url: string,
  method: string = 'GET',
  body?: any
): Promise<T> {
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (body && method !== 'GET') {
    options.body = JSON.stringify(body);
  }

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '';
  const fullUrl = url.startsWith('/') ? `${API_BASE}${url}` : url;

  const response = await fetch(fullUrl, options);

  if (!response.ok) {
    const error = new Error(`API request failed: ${response.status}`);
    throw error;
  }

  // 204 No Content の場合は空のオブジェクトを返す
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/**
 * サービス情報を更新する関数
 */
export async function updateService(serviceId: string, data: any) {
  return fetcher(`/api/services/${serviceId}`, 'PATCH', data);
}

/**
 * テストケースを更新する関数
 */
export async function updateTestCase(serviceId: string, caseId: string, data: any) {
  return fetcher(`/api/services/${serviceId}/test-cases/${caseId}`, 'PATCH', data);
}

/**
 * テストステップを更新する関数
 */
export async function updateTestStep(serviceId: string, caseId: string, stepId: string, data: any) {
  return fetcher(`/api/services/${serviceId}/test-cases/${caseId}/steps/${stepId}`, 'PATCH', data);
}
