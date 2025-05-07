"use client"

import * as React from 'react';
import { LayoutGridIcon, PlayIcon, CheckCircleIcon, ServerIcon } from 'lucide-react';

// 相対パスでのインポート
import { ProjectCard } from './components/molecules/ProjectCard';
import { StatsCard } from './components/molecules/StatsCard';
import { RecentTestRuns } from './components/molecules/RecentTestRuns';
import { QuickActions } from './components/molecules/QuickActions';

// useChainRuns フックと ChainRun 型をインポート
import { useChainRuns, ChainRun } from '@/hooks/useTestRuns';

// 型定義
interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

// プロジェクト一覧を取得するカスタムフック
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

// メモ化されたコンポーネント
const MemoizedProjectCard = React.memo(ProjectCard);
const MemoizedStatsCard = React.memo(StatsCard);
const MemoizedRecentTestRuns = React.memo(RecentTestRuns);
const MemoizedQuickActions = React.memo(QuickActions);

export default function Dashboard() {
  const { projects, isLoading: isLoadingProjects } = useProjects();
  // useChainRuns を使用してテスト実行履歴を取得
  const { chainRuns: recentRuns, isLoading: isLoadingRuns } = useChainRuns(''); // ダッシュボードでは特定のプロジェクトに紐づかないため空文字列を渡す

  // 統計情報を計算
  const dashboardStats = React.useMemo(() => {
    const totalProjects = projects?.length || 0;
    const totalRuns = recentRuns?.length || 0;
    
    let totalTests = 0;
    let passedTests = 0;

    recentRuns?.forEach(run => {
      totalTests += run.step_results?.length || 0;
      passedTests += run.step_results?.filter(step => step.passed).length || 0;
    });

    const successRate = totalTests > 0 ? Math.round((passedTests / totalTests) * 100) : 0;

    return {
      totalProjects,
      totalTests,
      totalRuns,
      successRate,
    };
  }, [projects, recentRuns]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">ダッシュボード</h1>
      
      {/* 統計情報 */}
      <div className="grid gap-3 grid-cols-2 md:grid-cols-2 lg:grid-cols-4 sm:gap-4">
        <MemoizedStatsCard
          title="プロジェクト数"
          value={dashboardStats.totalProjects}
          icon={<LayoutGridIcon />}
        />
        <MemoizedStatsCard
          title="テスト数"
          value={dashboardStats.totalTests}
          icon={<ServerIcon />}
        />
        <MemoizedStatsCard
          title="テスト実行数"
          value={dashboardStats.totalRuns}
          icon={<PlayIcon />}
        />
        <MemoizedStatsCard
          title="成功率"
          value={`${dashboardStats.successRate}%`}
          icon={<CheckCircleIcon />}
        />
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* プロジェクト一覧 */}
        <div className="md:col-span-2">
          <h2 className="text-xl font-semibold mb-3 md:mb-4">プロジェクト</h2>
          {isLoadingProjects ? (
            <div className="text-center py-6 md:py-8">読み込み中...</div>
          ) : projects && projects.length > 0 ? (
            <div className="grid gap-3 grid-cols-1 xs:grid-cols-2 sm:gap-4">
              {projects.map((project: Project) => (
                <MemoizedProjectCard key={project.id} project={project} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 border rounded-lg bg-background">
              <p className="text-muted-foreground">プロジェクトがありません</p>
              <p className="mt-2">新しいプロジェクトを作成してください</p>
            </div>
          )}
        </div>
        
        {/* サイドバー */}
        <div className="space-y-6">
          <MemoizedQuickActions />
          
          {isLoadingRuns ? (
            <div className="text-center py-4">読み込み中...</div>
          ) : (
            recentRuns && <MemoizedRecentTestRuns testRuns={recentRuns} />
          )}
        </div>
      </div>
    </div>
  );
}
