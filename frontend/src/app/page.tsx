"use client"

import * as React from 'react';
import { LayoutGridIcon, PlayIcon, CheckCircleIcon, ServerIcon } from 'lucide-react';

// 相対パスでのインポート
import { ProjectCard } from './components/molecules/ProjectCard';
import { StatsCard } from './components/molecules/StatsCard';
import { RecentTestRuns } from './components/molecules/RecentTestRuns';
import { QuickActions } from './components/molecules/QuickActions';

// 型定義
interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface TestRun {
  run_id: string;
  project_id: string;
  status: string;
  start_time: string;
  end_time?: string;
}

interface RunStats {
  totalTests: number;
  totalRuns: number;
  successRate: number;
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

// 最近のテスト実行を取得するカスタムフック
function useRecentTestRuns() {
  const [recentRuns, setRecentRuns] = React.useState<TestRun[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);
  const [stats, setStats] = React.useState({
    totalTests: 0,
    totalRuns: 0,
    successRate: 0,
  });

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
        setRecentRuns(data.runs || []);
        
        // 統計情報も一緒に取得
        setStats({
          totalTests: data.stats?.totalTests || 0,
          totalRuns: data.stats?.totalRuns || 0,
          successRate: data.stats?.successRate || 0,
        });
      } catch (err) {
        console.error('最近のテスト実行の取得に失敗しました:', err);
        setError(err instanceof Error ? err : new Error('不明なエラー'));
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchRecentRuns();
  }, []);
  
  return { recentRuns, isLoading, error, stats };
}

// メモ化されたコンポーネント
const MemoizedProjectCard = React.memo(ProjectCard);
const MemoizedStatsCard = React.memo(StatsCard);
const MemoizedRecentTestRuns = React.memo(RecentTestRuns);
const MemoizedQuickActions = React.memo(QuickActions);

export default function Dashboard() {
  const { projects, isLoading: isLoadingProjects } = useProjects();
  const { recentRuns, isLoading: isLoadingRuns, stats: runStats } = useRecentTestRuns();
  
  // 統計情報を計算
  const dashboardStats = React.useMemo(() => {
    return {
      totalProjects: projects?.length || 0,
      totalTests: runStats.totalTests,
      totalRuns: runStats.totalRuns,
      successRate: runStats.successRate,
    };
  }, [projects, runStats]);

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
            <MemoizedRecentTestRuns testRuns={recentRuns} />
          )}
        </div>
      </div>
    </div>
  );
}
