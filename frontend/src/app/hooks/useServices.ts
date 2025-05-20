import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface Service {
  id: string;
  name: string;
  description?: string;
  base_url?: string;
  created_at: string;
  updated_at: string;
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
      console.error('Failed to create service:', err);
      throw err;
    }
  };
  
  const deleteService = async (serviceId: string) => {
    try {
      await fetcher(`/api/services/${serviceId}`, 'DELETE');
      mutate();
    } catch (err) {
      console.error(`Failed to delete service ${serviceId}:`, err);
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
