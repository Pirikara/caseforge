"use client"

import * as React from 'react';
import Link from 'next/link';
import { PlusIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from 'lucide-react';
import { Button } from '../ui/button';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';

// プロジェクトの型定義
interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

// テスト実行の型定義
interface TestRun {
  run_id: string;
  project_id: string;
  project_name?: string;
  status: 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
}

// プロジェクト一覧を取得するためのカスタムフック
function useProjects() {
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    async function fetchProjects() {
      try {
        setIsLoading(true);
        const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
        const response = await fetch(`${API}/api/projects/`);
        
        if (!response.ok) {
          throw new Error(`API ${response.status}`);
        }
        
        const data = await response.json();
        setProjects(data);
      } catch (err) {
        console.error('プロジェクト一覧の取得に失敗しました:', err);
        setError(err instanceof Error ? err : new Error('不明なエラー'));
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchProjects();
  }, []);
  
  return { projects, isLoading, error };
}

// 最近のテスト実行を取得するためのカスタムフック
function useRecentTestRuns() {
  const [recentRuns, setRecentRuns] = React.useState<TestRun[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    async function fetchRecentRuns() {
      try {
        setIsLoading(true);
        const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
        const response = await fetch(`${API}/api/projects/recent-runs?limit=5`);
        
        if (!response.ok) {
          throw new Error(`API ${response.status}`);
        }
        
        const data = await response.json();
        setRecentRuns(data);
      } catch (err) {
        console.error('最近のテスト実行の取得に失敗しました:', err);
        setError(err instanceof Error ? err : new Error('不明なエラー'));
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchRecentRuns();
  }, []);
  
  return { recentRuns, isLoading, error };
}

export function Sidebar({ className }: { className?: string }) {
  const { projects, isLoading: projectsLoading, error: projectsError } = useProjects();
  const { recentRuns, isLoading: runsLoading, error: runsError } = useRecentTestRuns();
  
  return (
    <aside className={`w-64 border-r border-border bg-background p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">プロジェクト</h2>
        <Button size="sm" asChild>
          <Link href="/projects/new">
            <PlusIcon className="h-4 w-4 mr-1" />
            新規
          </Link>
        </Button>
      </div>
      
      {projectsLoading ? (
        <div>読み込み中...</div>
      ) : projectsError ? (
        <div>エラーが発生しました</div>
      ) : (
        <ul className="space-y-1">
          {projects?.map((project) => (
            <li key={project.id}>
              <Link
                href={`/projects/${project.id}`}
                className="block p-2 rounded hover:bg-accent hover:text-accent-foreground"
              >
                {project.name}
              </Link>
            </li>
          ))}
        </ul>
      )}
      
      <div className="mt-8">
        <h3 className="text-sm font-semibold mb-2">最近のテスト実行</h3>
        {runsLoading ? (
          <div className="text-xs text-muted-foreground">読み込み中...</div>
        ) : runsError ? (
          <div className="text-xs text-muted-foreground">テスト実行の取得に失敗しました</div>
        ) : recentRuns && recentRuns.length > 0 ? (
          <ul className="space-y-2">
            {recentRuns.map((run) => (
              <li key={run.run_id}>
                <Link
                  href={`/projects/${run.project_id}/runs/${run.run_id}`}
                  className="flex items-center gap-2 p-2 rounded text-sm hover:bg-accent hover:text-accent-foreground"
                >
                  {run.status === 'completed' ? (
                    <CheckCircleIcon className="h-4 w-4 text-green-500 flex-shrink-0" />
                  ) : run.status === 'failed' ? (
                    <XCircleIcon className="h-4 w-4 text-red-500 flex-shrink-0" />
                  ) : (
                    <ClockIcon className="h-4 w-4 text-yellow-500 flex-shrink-0" />
                  )}
                  <div className="overflow-hidden">
                    <div className="truncate font-medium">{run.project_name || run.project_id}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {formatDistanceToNow(new Date(run.start_time), { addSuffix: true, locale: ja })}
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-xs text-muted-foreground">テスト実行履歴がありません</div>
        )}
      </div>
    </aside>
  );
}