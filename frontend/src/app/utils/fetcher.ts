const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

/**
 * 共通のfetcher関数
 * SWRで使用するためのfetcher関数です
 */
export const fetcher = (url: string) =>
  fetch(`${API}${url}`).then(r => {
    if (!r.ok) throw new Error(`API ${r.status}`);
    return r.json();
  });