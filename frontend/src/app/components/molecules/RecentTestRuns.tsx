"use client"

import * as React from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';
import { CheckCircleIcon, XCircleIcon, ClockIcon } from 'lucide-react';
import { TestRun } from '@/hooks/useTestRuns';

interface RecentTestRunsProps {
  testRuns: TestRun[];
}

export function RecentTestRuns({ testRuns }: RecentTestRunsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>最近のテスト実行</CardTitle>
      </CardHeader>
      <CardContent>
        {testRuns && testRuns.length > 0 ? (
          <div className="space-y-4">
            {testRuns.slice(0, 5).map((run) => (
              <Link
                key={run.id}
                href={`/projects/${run.project_id}/runs/${run.run_id}`}
                className="flex items-center justify-between p-2 rounded-md hover:bg-accent"
              >
                <div className="flex items-center gap-2">
                  {run.status === 'completed' ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-500" />
                  ) : run.status === 'failed' ? (
                    <XCircleIcon className="h-5 w-5 text-red-500" />
                  ) : (
                    <ClockIcon className="h-5 w-5 text-yellow-500" />
                  )}
                  <div>
                    <div className="font-medium">実行 #{run.run_id}</div>
                    <div className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(run.start_time), { addSuffix: true, locale: ja })}
                    </div>
                  </div>
                </div>
                <div className="text-sm">
                  {run.status === 'completed' ? '完了' : run.status === 'failed' ? '失敗' : '実行中'}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-4 text-muted-foreground">
            テスト実行履歴がありません
          </div>
        )}
      </CardContent>
    </Card>
  );
}