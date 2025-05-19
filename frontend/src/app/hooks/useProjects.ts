import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface Service {
  id: string;
  name: string;
  description?: string;
  base_url?: string; // base_url プロパティを追加
  created_at: string;
}

export function useServices() {
  const { data, error, isLoading, mutate } = useSWR<Service[]>('/api/services/', fetcher);
  
  const deleteService = async (serviceId: string) => {
    try {
      await fetcher(`/api/services/${serviceId}`, 'DELETE');
      // 削除成功後、SWRのキャッシュを更新して再フェッチ
      mutate();
    } catch (err) {
      console.error(`Failed to delete service ${serviceId}:`, err);
      throw err; // エラーを呼び出し元に伝える
    }
  };

  return {
    services: data,
    isLoading,
    error,
    mutate,
    deleteService, // 削除関数を追加
  };
}
