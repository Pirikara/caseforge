import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface Service {
  id: number;
  name: string;
  description?: string;
  base_url?: string;
  created_at: string;
  updated_at: string;
  has_schema?: boolean;
}

export function useServices() {
  const { data, error, isLoading, mutate } = useSWR<Service[]>(
    '/api/services/',
    fetcher
  );
  
  const createService = async (serviceData: Partial<Service>) => {
    try {
      const newService = await fetcher('/api/services/', 'POST', serviceData);
      mutate();
      return newService;
    } catch (err) {
      throw err;
    }
  };
  
  const deleteService = async (serviceId: number) => {
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
    createService,
    deleteService,
  };
}
