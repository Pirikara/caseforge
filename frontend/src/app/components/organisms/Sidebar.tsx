"use client"

import * as React from 'react';
import Link from 'next/link';
import { PlusIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from 'lucide-react';
import { Button } from '../ui/button';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';
import { useTheme } from 'next-themes';
import { MoonIcon, SunIcon } from 'lucide-react';

interface Service {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface TestRun {
  run_id: string;
  service_id: string;
  service_name?: string;
  status: 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
}

import { useServices } from '@/hooks/useServices';

function useRecentTestRuns() {
  const [recentRuns, setRecentRuns] = React.useState<TestRun[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    async function fetchRecentRuns() {
      try {
        setIsLoading(true);
        const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
        const response = await fetch(`${API}/api/services/recent-runs?limit=5`);

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
  const { services, isLoading: servicesLoading, error: servicesError } = useServices();
  const { recentRuns, isLoading: runsLoading, error: runsError } = useRecentTestRuns();
  const { theme, setTheme } = useTheme();

  return (
    <aside className={`w-64 border-r border-border bg-background p-4 fixed top-0 left-0 h-full overflow-y-auto ${className}`}>
      <Link href="/" className="font-bold text-xl mb-4 block">Caseforge</Link>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">サービス</h2>
        {/* 新規作成ボタンを削除 */}
      </div>

      {servicesLoading ? (
        <div>読み込み中...</div>
      ) : servicesError ? (
        <div>エラーが発生しました</div>
      ) : (
        <ul className="space-y-1">
          {services?.map((service) => (
            <li key={service.id}>
              <Link
                href={`/services/${service.id}?tab=test-chains`}
                className="block p-2 rounded hover:bg-accent hover:text-accent-foreground"
              >
                {service.name}
              </Link>
            </li>
          ))}
        </ul>
      )}

      {/* 最近のテスト実行セクションを削除 */}
      <div className="mt-auto p-4 border-t">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          {theme === 'dark' ? <SunIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}
        </Button>
      </div>
    </aside>
  );
}
