"use client"

import * as React from 'react';
import { LayoutGridIcon, PlayIcon, CheckCircleIcon, ServerIcon, AlertTriangleIcon } from 'lucide-react'; // AlertTriangleIconをインポート
import Link from 'next/link';

import { ServiceCard } from './components/molecules/ServiceCard';
import { StatsCard } from './components/molecules/StatsCard';
import { RecentTestRuns } from './components/molecules/RecentTestRuns';
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import { useTestRuns, TestRun } from '@/hooks/useTestRuns';
import { useServices, Service } from '@/hooks/useServices';

const MemoizedServiceCard = React.memo(ServiceCard);
const MemoizedStatsCard = React.memo(StatsCard);
const MemoizedRecentTestRuns = React.memo(RecentTestRuns);

export default function Dashboard() {
  const { services, isLoading: isLoadingServices } = useServices();
  const { testRuns: recentRuns, isLoading: isLoadingRuns } = useTestRuns('');

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

  const servicesWithoutSchema = services?.filter(service => !service.has_schema) || []; // servicesWithoutSchema変数を定義

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">ダッシュボード</h1>
      
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
      
      {/* 推奨アクション */}
      {isLoadingServices ? (
        <div className="text-center py-4">読み込み中...</div>
      ) : servicesWithoutSchema.length > 0 ? (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">推奨アクション</h2>
          <div className="flex flex-col gap-4">
            {servicesWithoutSchema.map(service => (
              <Link href={`/services/${service.id}/schema`} key={service.id}>
                <Card key={service.id} className="border-yellow-500 hover:bg-muted/50 transition-colors">
                  <CardHeader className="flex flex-row items-center space-x-4 p-4">
                    <AlertTriangleIcon className="h-8 w-8 text-yellow-500" />
                    <div className="flex-1">
                      <CardTitle className="text-lg text-primary">{service.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">
                        スキーマがアップロードされていません。
                      </p>
                    </div>
                  </CardHeader>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      ) : services && services.length === 0 ? (
         <div className="border rounded-lg p-4 text-muted-foreground">
           <p>新しいサービスを作成して、スキーマをアップロードしましょう。</p>
         </div>
      ) : null /* スキーマがないサービスがない場合は推奨アクションセクション全体を非表示 */ }
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* サイドバー */}
        <div className="md:col-span-2 space-y-6">
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
