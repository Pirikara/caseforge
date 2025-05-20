"use client"

import * as React from 'react';
import Link from 'next/link';
import { PlusIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from 'lucide-react';
import { Button } from '../ui/button';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';

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

  return (
    <aside className={`w-64 border-r border-border bg-background p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">サービス</h2>
        <Button size="sm" asChild>
          <Link href="/services/new">
            <PlusIcon className="h-4 w-4 mr-1" />
            新規
          </Link>
        </Button>
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
                  href={`/services/${run.service_id}/runs/${run.run_id}`}
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
                    <div className="truncate font-medium">{run.service_name || run.service_id}</div>
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
