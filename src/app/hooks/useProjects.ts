import useSWR from 'swr';

const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
const fetcher = (url: string) =>
  fetch(`${API}${url}`).then(r => {
    if (!r.ok) throw new Error(`API ${r.status}`);
    return r.json();
  });

export function useProjects() {
  const { data, error, isLoading, mutate } = useSWR('/api/projects/', fetcher);
  
  return {
    projects: data,
    isLoading,
    error,
    mutate,
  };
}