import useSWR from 'swr';
import { fetcher } from '@/utils/fetcher';

export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

export function useProjects() {
  const { data, error, isLoading, mutate } = useSWR<Project[]>('/api/projects/', fetcher);
  
  return {
    projects: data,
    isLoading,
    error,
    mutate,
  };
}