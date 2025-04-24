"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useProjects } from '@/hooks/useProjects';
import { useTestChains } from '@/hooks/useTestChains';
import { useChainRuns } from '@/hooks/useTestRuns';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { 
  PlayIcon, 
  FileTextIcon, 
  UploadIcon, 
  CheckCircleIcon, 
  XCircleIcon, 
  ClockIcon 
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  
  const { projects } = useProjects();
  const { testChains, isLoading: isLoadingTestChains } = useTestChains(projectId);
  const { chainRuns, isLoading: isLoadingChainRuns } = useChainRuns(projectId);
  
  const project = React.useMemo(() => {
    if (!projects) return null;
    return projects.find(p => p.id === projectId);
  }, [projects, projectId]);
  
  if (!project) {
    return (
      <div className="text-center py-8">
        <p>プロジェクトが見つかりません</p>
        <Button asChild className="mt-4">
          <Link href="/projects">プロジェクト一覧に戻る</Link>
        </Button>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">{project.name}</h1>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href={`/projects/${projectId}/schema`}>
              <UploadIcon className="h-4 w-4 mr-2" />
              スキーマ更新
            </Link>
          </Button>
          <Button asChild>
            <Link href={`/projects/${projectId}/generate`}>
              <FileTextIcon className="h-4 w-4 mr-2" />
              テスト生成
            </Link>
          </Button>
          <Button asChild>
            <Link href={`/projects/${projectId}/run`}>
              <PlayIcon className="h-4 w-4 mr-2" />
              テスト実行
            </Link>
          </Button>
        </div>
      </div>
      
      {project.description && (
        <p className="text-muted-foreground">{project.description}</p>
      )}
      
      <div className="grid gap-4 sm:gap-6 grid-cols-1 md:grid-cols-2">
        {/* プロジェクト情報 */}
        <Card>
          <CardHeader>
            <CardTitle>プロジェクト情報</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4">
              <div className="flex justify-between">
                <dt className="font-medium">プロジェクトID</dt>
                <dd className="text-muted-foreground">{projectId}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">作成日</dt>
                <dd className="text-muted-foreground">
                  {formatDistanceToNow(new Date(project.created_at), { addSuffix: true, locale: ja })}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">テストチェーン数</dt>
                <dd className="text-muted-foreground">{testChains?.length || 0}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">テスト実行数</dt>
                <dd className="text-muted-foreground">{chainRuns?.length || 0}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
        
        {/* 最近のテスト実行 */}
        <Card>
          <CardHeader>
            <CardTitle>最近のテスト実行</CardTitle>
            <CardDescription>
              <Link href={`/projects/${projectId}/runs`} className="text-sm hover:underline">
                すべて表示
              </Link>
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingChainRuns ? (
              <div className="text-center py-4">読み込み中...</div>
            ) : chainRuns && chainRuns.length > 0 ? (
              <div className="space-y-2">
                {chainRuns.slice(0, 5).map((run) => (
                  <Link
                    key={run.id}
                    href={`/projects/${projectId}/runs/${run.run_id}`}
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
      </div>
      
      {/* テストチェーン一覧 */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">テストチェーン</h2>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/projects/${projectId}/chains`}>
              すべて表示
            </Link>
          </Button>
        </div>
        
        {isLoadingTestChains ? (
          <div className="text-center py-6 md:py-8">読み込み中...</div>
        ) : testChains && testChains.length > 0 ? (
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>チェーン名</TableHead>
                  <TableHead>ステップ数</TableHead>
                  <TableHead>メソッド順序</TableHead>
                  <TableHead className="w-[100px]">アクション</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {testChains.slice(0, 5).map((chain) => (
                  <TableRow key={chain.id}>
                    <TableCell className="font-medium">{chain.name}</TableCell>
                    <TableCell>{chain.steps.length}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {chain.steps.map((step, index) => (
                          <span key={index} className={`px-2 py-1 rounded text-xs font-medium ${
                            step.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                            step.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                            step.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                            step.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                            'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
                          }`}>
                            {step.method}
                            {index < chain.steps.length - 1 && <span className="ml-1">→</span>}
                          </span>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/projects/${projectId}/chains/${chain.chain_id}`}>
                          詳細
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <div className="text-center py-8 border rounded-lg bg-background">
            <p className="text-muted-foreground">テストチェーンがありません</p>
            <p className="mt-2">テストチェーン生成を実行してください</p>
          </div>
        )}
      </div>
    </div>
  );
}