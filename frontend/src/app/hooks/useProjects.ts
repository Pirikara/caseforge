import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface Service {
  id: string;
  name: string;
  description?: string;
  base_url?: string;
  created_at: string;
}

export function useServices() {
  const { data, error, isLoading, mutate } = useSWR<Service[]>('/api/services/', fetcher);
  
  const deleteService = async (serviceId: string) => {
    try {
      await fetcher(`/api/services/${serviceId}`, 'DELETE');
      mutate();
    } catch (err) {
      throw err;
    }
  };

  return {
    services: data,
    isLoading,
    error,
    mutate,
    deleteService,
  };
}
