"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useProjects } from '@/hooks/useProjects';
import { useTestRuns } from '@/hooks/useTestRuns';
import { useTestCases } from '@/hooks/useTestCases';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeftIcon, 
  CheckCircleIcon, 
  XCircleIcon, 
  ClockIcon,
  SearchIcon
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  Tooltip, 
  Legend 
} from 'recharts';

export default function TestRunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const runId = params.run_id as string;
  
  const { projects } = useProjects();
  const { testRuns, isLoading: isLoadingRuns } = useTestRuns(projectId);
  const { testCases, isLoading: isLoadingTestCases } = useTestCases(projectId);
  
  const [searchQuery, setSearchQuery] = React.useState('');
  
  const project = React.useMemo(() => {
    if (!projects) return null;
    return projects.find(p => p.id === projectId);
  }, [projects, projectId]);
  
  const testRun = React.useMemo(() => {
    if (!testRuns) return null;
    return testRuns.find(run => run.run_id === runId);
  }, [testRuns, runId]);
  
  // 検索フィルタリング
  const filteredResults = React.useMemo(() => {
    if (!testRun?.results) return [];
    
    return testRun.results.filter(result => {
      // テストケースを取得
      const testCase = testCases?.find(tc => tc.id === result.test_case_id);
      if (!testCase) return false;
      
      // 検索フィルター
      return (
        testCase.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        testCase.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
        testCase.method.toLowerCase().includes(searchQuery.toLowerCase())
      );
    });
  }, [testRun?.results, testCases, searchQuery]);
  
  // 円グラフデータの作成
  const pieChartData = React.useMemo(() => {
    if (!testRun?.results) return [];
    
    const passedCount = testRun.results.filter(r => r.passed).length;
    const failedCount = testRun.results.length - passedCount;
    
    return [
      { name: '成功', value: passedCount, color: '#10b981' },
      { name: '失敗', value: failedCount, color: '#ef4444' },
    ].filter(item => item.value > 0);
  }, [testRun?.results]);
  
  if (isLoadingRuns || isLoadingTestCases) {
    return <div className="text-center py-8">読み込み中...</div>;
  }
  
  if (!project || !testRun) {
    return (
      <div className="text-center py-8">
        <p>テスト実行が見つかりません</p>
        <Button asChild className="mt-4">
          <Link href={`/projects/${projectId}/runs`}>テスト実行一覧に戻る</Link>
        </Button>
      </div>
    );
  }
  
  // JSONを整形して表示
  const formatJSON = (json: any) => {
    try {
      return JSON.stringify(json, null, 2);
    } catch (e) {
      return String(json);
    }
  };
  
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/projects/${projectId}/runs`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            テスト実行一覧に戻る
          </Link>
        </Button>
      </div>
      
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">テスト実行 #{runId}</h1>
        <div className="flex items-center gap-2">
          {testRun.status === 'completed' ? (
            <div className="flex items-center text-green-500 gap-1">
              <CheckCircleIcon className="h-5 w-5" />
              <span>完了</span>
            </div>
          ) : testRun.status === 'failed' ? (
            <div className="flex items-center text-red-500 gap-1">
              <XCircleIcon className="h-5 w-5" />
              <span>失敗</span>
            </div>
          ) : (
            <div className="flex items-center text-yellow-500 gap-1">
              <ClockIcon className="h-5 w-5" />
              <span>実行中</span>
            </div>
          )}
        </div>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>テスト実行情報</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4">
              <div className="flex justify-between">
                <dt className="font-medium">プロジェクト</dt>
                <dd className="text-muted-foreground">{project.name}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">実行ID</dt>
                <dd className="text-muted-foreground">{runId}</dd>
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
                <dt className="font-medium">テスト数</dt>
                <dd className="text-muted-foreground">{testRun.results?.length || 0}</dd>
              </div>
              {testRun.status === 'completed' && (
                <div className="flex justify-between">
                  <dt className="font-medium">成功率</dt>
                  <dd className="text-muted-foreground">
                    {testRun.results && testRun.results.length > 0 ? (
                      `${Math.round((testRun.results.filter(r => r.passed).length / testRun.results.length) * 100)}%`
                    ) : '0%'}
                  </dd>
                </div>
              )}
            </dl>
          </CardContent>
        </Card>
        
        {pieChartData.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>テスト結果</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieChartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {pieChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
      
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold">テスト結果詳細</h2>
          <div className="relative w-64">
            <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="テストケースを検索..."
              className="pl-8"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
        
        {filteredResults.length > 0 ? (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[80px]">結果</TableHead>
                  <TableHead className="w-[80px]">メソッド</TableHead>
                  <TableHead>パス</TableHead>
                  <TableHead className="w-[100px]">ステータス</TableHead>
                  <TableHead className="w-[100px]">レスポンス時間</TableHead>
                  <TableHead className="w-[100px]">アクション</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredResults.map((result) => {
                  // テストケースを取得
                  const testCase = testCases?.find(tc => tc.id === result.test_case_id);
                  if (!testCase) return null;
                  
                  return (
                    <TableRow key={result.id}>
                      <TableCell>
                        {result.passed ? (
                          <CheckCircleIcon className="h-5 w-5 text-green-500" />
                        ) : (
                          <XCircleIcon className="h-5 w-5 text-red-500" />
                        )}
                      </TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          testCase.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200' :
                          testCase.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200' :
                          testCase.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200' :
                          testCase.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200' :
                          'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200'
                        }`}>
                          {testCase.method}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        <div className="flex flex-col">
                          <span>{testCase.path}</span>
                          <span className="text-xs text-muted-foreground truncate max-w-[300px]">
                            {testCase.title}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className={result.passed ? 'text-green-500' : 'text-red-500'}>
                          {result.status_code}
                        </span>
                      </TableCell>
                      <TableCell>
                        {result.response_time.toFixed(2)} ms
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            const dialog = document.getElementById(`result-dialog-${result.id}`);
                            if (dialog instanceof HTMLDialogElement) {
                              dialog.showModal();
                            }
                          }}
                        >
                          詳細
                        </Button>
                        
                        <dialog
                          id={`result-dialog-${result.id}`}
                          className="p-0 rounded-lg shadow-lg backdrop:bg-black/50 w-full max-w-3xl"
                        >
                          <div className="p-6">
                            <div className="flex justify-between items-center mb-4">
                              <h3 className="text-lg font-semibold">テスト結果詳細</h3>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const dialog = document.getElementById(`result-dialog-${result.id}`);
                                  if (dialog instanceof HTMLDialogElement) {
                                    dialog.close();
                                  }
                                }}
                              >
                                ✕
                              </Button>
                            </div>
                            
                            <div className="grid gap-4">
                              <div className="flex justify-between">
                                <span className="font-medium">テストケース</span>
                                <span>{testCase.title}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="font-medium">メソッド</span>
                                <span>{testCase.method}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="font-medium">パス</span>
                                <span className="font-mono">{testCase.path}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="font-medium">結果</span>
                                <span className={result.passed ? 'text-green-500' : 'text-red-500'}>
                                  {result.passed ? '成功' : '失敗'}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="font-medium">ステータスコード</span>
                                <span>{result.status_code}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="font-medium">レスポンス時間</span>
                                <span>{result.response_time.toFixed(2)} ms</span>
                              </div>
                            </div>
                            
                            <Tabs defaultValue="response" className="mt-4">
                              <TabsList className="grid w-full grid-cols-2">
                                <TabsTrigger value="response">レスポンス</TabsTrigger>
                                <TabsTrigger value="error">エラー</TabsTrigger>
                              </TabsList>
                              <TabsContent value="response" className="mt-2">
                                <div className="bg-muted p-4 rounded-md overflow-auto max-h-80">
                                  <pre className="font-mono text-sm">
                                    {result.response_body ? formatJSON(result.response_body) : 'レスポンスボディなし'}
                                  </pre>
                                </div>
                              </TabsContent>
                              <TabsContent value="error" className="mt-2">
                                <div className="bg-muted p-4 rounded-md overflow-auto max-h-80">
                                  <pre className="font-mono text-sm text-red-500">
                                    {result.error_message || 'エラーメッセージなし'}
                                  </pre>
                                </div>
                              </TabsContent>
                            </Tabs>
                          </div>
                        </dialog>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        ) : (
          <div className="text-center py-8 border rounded-lg bg-background">
            <p className="text-muted-foreground">テスト結果が見つかりません</p>
            {searchQuery ? (
              <p className="mt-2">検索条件を変更してください</p>
            ) : (
              <p className="mt-2">テスト実行が完了していないか、結果がありません</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}