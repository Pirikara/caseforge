"use client"

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { format } from 'date-fns';
import { TestRun } from '@/hooks/useTestRuns';
import { CheckCircleIcon, XCircleIcon, ClockIcon } from 'lucide-react';

interface TestRunSummaryProps {
  testRun: TestRun;
  serviceName: string;
}

export default function TestRunSummary({ testRun, serviceName }: TestRunSummaryProps) {
  // 成功率の計算
  const successRate = React.useMemo(() => {
    if (!testRun.test_case_results || testRun.test_case_results.length === 0) return 0;
    const passedCount = testRun.test_case_results.filter(r => r.status === 'passed').length;
    return Math.round((passedCount / testRun.test_case_results.length) * 100);
  }, [testRun.test_case_results]);

  // テスト実行時間の計算（ミリ秒）
  const executionTime = React.useMemo(() => {
    if (!testRun.start_time || !testRun.end_time) return null;
    const start = new Date(testRun.start_time).getTime();
    const end = new Date(testRun.end_time).getTime();
    return end - start;
  }, [testRun.start_time, testRun.end_time]);

  // ミリ秒を読みやすい形式に変換
  const formatExecutionTime = (ms: number | null) => {
    if (ms === null) return '計測中...';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}秒`;
    const minutes = Math.floor(ms / 60000);
    const seconds = ((ms % 60000) / 1000).toFixed(1);
    return `${minutes}分 ${seconds}秒`;
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>テスト実行情報</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="space-y-4">
            <div className="flex justify-between">
              <dt className="font-medium">サービス</dt>
              <dd className="text-muted-foreground">{serviceName}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="font-medium">実行ID</dt>
              <dd className="text-muted-foreground">{testRun.run_id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="font-medium">ステータス</dt>
              <dd>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  testRun.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                  testRun.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                  'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
                }`}>
                  {testRun.status === 'completed' ? '完了' : 
                   testRun.status === 'failed' ? '失敗' : '実行中'}
                </span>
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="font-medium">開始時間</dt>
              <dd className="text-muted-foreground">
                {format(new Date(testRun.start_time), 'yyyy/MM/dd HH:mm:ss')}
              </dd>
            </div>
            {testRun.end_time && (
              <div className="flex justify-between">
                <dt className="font-medium">終了時間</dt>
                <dd className="text-muted-foreground">
                  {format(new Date(testRun.end_time), 'yyyy/MM/dd HH:mm:ss')}
                </dd>
              </div>
            )}
            <div className="flex justify-between">
              <dt className="font-medium">実行時間</dt>
              <dd className="text-muted-foreground">
                {formatExecutionTime(executionTime)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="font-medium">テスト数</dt>
              <dd className="text-muted-foreground">{testRun.test_case_results?.length || 0}</dd>
            </div>
            {testRun.status !== 'running' && (
              <div className="flex justify-between">
                <dt className="font-medium">成功率</dt>
                <dd className={`font-medium ${
                  successRate > 80 ? 'text-green-600 dark:text-green-400' : 
                  successRate > 50 ? 'text-yellow-600 dark:text-yellow-400' : 
                  'text-red-600 dark:text-red-400'
                }`}>
                  {successRate}%
                </dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>テスト結果サマリー</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col items-center justify-center p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
                <span className="text-lg font-medium">成功</span>
              </div>
              <span className="text-3xl font-bold text-green-600 dark:text-green-400">
                {testRun.test_case_results?.filter(r => r.status === 'passed').length || 0}
              </span>
            </div>
            <div className="flex flex-col items-center justify-center p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <XCircleIcon className="h-5 w-5 text-red-500" />
                <span className="text-lg font-medium">失敗</span>
              </div>
              <span className="text-3xl font-bold text-red-600 dark:text-red-400">
                {testRun.test_case_results?.filter(r => r.status === 'failed').length || 0}
              </span>
            </div>
            <div className="flex flex-col items-center justify-center p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <ClockIcon className="h-5 w-5 text-yellow-500" />
                <span className="text-lg font-medium">スキップ</span>
              </div>
              <span className="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
                {testRun.test_case_results?.filter(r => r.status === 'skipped').length || 0}
              </span>
            </div>
            <div className="flex flex-col items-center justify-center p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg font-medium">合計</span>
              </div>
              <span className="text-3xl font-bold">
                {testRun.test_case_results?.length || 0}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
