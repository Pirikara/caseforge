"use client"

import * as React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { PlusIcon, CheckCircleIcon, XCircleIcon, ClockIcon, HomeIcon, BoxIcon } from 'lucide-react';
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

export function Sidebar({ className, showLogo = true }: { className?: string; showLogo?: boolean }) {
  const { services, isLoading: servicesLoading, error: servicesError } = useServices();
  const { recentRuns, isLoading: runsLoading, error: runsError } = useRecentTestRuns();
  const { theme, setTheme } = useTheme();

  return (
    <aside className={`w-64 border-r border-border bg-background fixed top-0 left-0 h-full overflow-y-auto flex flex-col ${className}`}>
      {showLogo && (
        <div className="flex items-center h-16 border-b border-border px-4">
          <Link href="/">
            {theme === 'dark' ? (
              <Image src="/logo/caseforge-logo-dark.svg" alt="Caseforge Logo Dark" width={48} height={48} />
            ) : (
              <Image src="/logo/caseforge-logo-light.svg" alt="Caseforge Logo Light" width={48} height={48} />
            )}
          </Link>
        </div>
      )}

      <nav className="p-4 space-y-1">
        <Link href="/" className="flex items-center p-2 rounded hover:bg-accent hover:text-accent-foreground">
          <HomeIcon className="w-6 mr-2" /> ダッシュボード
        </Link>
        <Link href="/services" className="flex items-center p-2 rounded hover:bg-accent hover:text-accent-foreground">
          <BoxIcon className="w-6 mr-2" /> すべてのサービス
        </Link>
      </nav>

      <div className="border-b border-border mx-4 my-2"></div>

      <div className="p-4 flex-grow overflow-y-auto">
        <h3 className="text-sm font-semibold mb-2 text-muted-foreground">最近使ったサービス</h3>
        {servicesLoading ? (
          <div>読み込み中...</div>
        ) : servicesError ? (
          <div>エラーが発生しました</div>
        ) : (
          <ul className="space-y-1">
            {services?.slice(0, 5).map((service) => (
              <li key={service.id}>
                <Link
                  href={`/services/${service.id}?tab=test-chains`}
                  className="block p-2 rounded hover:bg-accent hover:text-accent-foreground text-sm"
                >
                  {service.name}
                </Link>
              </li>
            ))}
            {services && services.length > 5 && (
              <li>
                <Link
                  href="/services"
                  className="block p-2 rounded hover:bg-accent hover:text-accent-foreground text-sm text-blue-500"
                >
                  すべて表示 →
                </Link>
              </li>
            )}
          </ul>
        )}
      </div>

      <div className="p-4 border-t border-border flex justify-start items-center">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="w-full flex justify-start items-center"
        >
          {theme === 'dark' ? (
            <>
              <SunIcon className="h-4 w-4 mr-2" /> ライトモードに切り替え
            </>
          ) : (
            <>
              <MoonIcon className="h-4 w-4 mr-2" /> ダークモードに切り替え
            </>
          )}
        </Button>
      </div>
    </aside>
  );
}
