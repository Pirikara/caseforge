"use client"

import * as React from 'react';
import { LayoutGridIcon, PlayIcon, CheckCircleIcon, ServerIcon } from 'lucide-react';

// 相対パスでのインポート
import { ServiceCard } from './components/molecules/ServiceCard';
import { StatsCard } from './components/molecules/StatsCard';
import { RecentTestRuns } from './components/molecules/RecentTestRuns';
import { QuickActions } from './components/molecules/QuickActions';

// useTestRuns フックと TestRun 型をインポート
import { useTestRuns, TestRun } from '@/hooks/useTestRuns';
// useServices フックと Service 型をインポート
import { useServices, Service } from '@/hooks/useServices';

// メモ化されたコンポーネント
const MemoizedServiceCard = React.memo(ServiceCard);
const MemoizedStatsCard = React.memo(StatsCard);
const MemoizedRecentTestRuns = React.memo(RecentTestRuns);
const MemoizedQuickActions = React.memo(QuickActions);

export default function Dashboard() {
  const { services, isLoading: isLoadingServices } = useServices();
  // useTestRuns を使用してテスト実行履歴を取得
  const { testRuns: recentRuns, isLoading: isLoadingRuns } = useTestRuns(''); // ダッシュボードでは特定のサービスに紐づかないため空文字列を渡す

  // 統計情報を計算
  const dashboardStats = React.useMemo(() => {
    const totalServices = services?.length || 0;
    const totalRuns = recentRuns?.length || 0;
    
    let totalTests = 0;
    let passedTests = 0;

    recentRuns?.forEach(run => {
      totalTests += run.test_case_results?.reduce((sum, caseResult) => sum + (caseResult.step_results?.length || 0), 0) || 0;
      passedTests += run.test_case_results?.reduce((sum, caseResult) => sum + (caseResult.step_results?.filter(step => step.passed).length || 0), 0) || 0;
    });

    const successRate = totalTests > 0 ? Math.round((passedTests / totalTests) * 100) : 0;

    return {
      totalServices,
      totalTests,
      totalRuns,
      successRate,
    };
  }, [services, recentRuns]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">ダッシュボード</h1>
      
      {/* 統計情報 */}
      <div className="grid gap-3 grid-cols-2 md:grid-cols-2 lg:grid-cols-4 sm:gap-4">
        <MemoizedStatsCard
          title="サービス数"
          value={dashboardStats.totalServices}
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
        {/* サービス一覧 */}
        <div className="md:col-span-2">
          <h2 className="text-xl font-semibold mb-3 md:mb-4">サービス</h2>
          {isLoadingServices ? (
            <div className="text-center py-6 md:py-8">読み込み中...</div>
          ) : services && services.length > 0 ? (
            <div className="grid gap-3 grid-cols-1 xs:grid-cols-2 sm:gap-4">
              {services.map((service: Service) => (
                <MemoizedServiceCard key={service.id} service={service} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 border rounded-lg bg-background">
              <p className="text-muted-foreground">サービスがありません</p>
              <p className="mt-2">新しいサービスを作成してください</p>
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
