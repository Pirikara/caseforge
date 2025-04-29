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
  
  const deleteProject = async (projectId: string) => {
    try {
      await fetcher(`/api/projects/${projectId}`, 'DELETE');
      // 削除成功後、SWRのキャッシュを更新して再フェッチ
      mutate();
    } catch (err) {
      console.error(`Failed to delete project ${projectId}:`, err);
      throw err; // エラーを呼び出し元に伝える
    }
  };

  return {
    projects: data,
    isLoading,
    error,
    mutate,
    deleteProject, // 削除関数を追加
  };
}