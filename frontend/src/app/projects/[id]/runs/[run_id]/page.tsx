"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useServices } from '@/hooks/useServices';
import { useTestRuns } from '@/hooks/useTestRuns';
import { TestCaseResult, StepResult, TestCase } from '@/hooks/useTestRuns'; // StepResult, TestCase を追加
import { useTestCases } from '@/hooks/useTestCases';
import { useTestSuiteDetail } from '@/hooks/useTestChains'; // useTestChain を useTestSuiteDetail に変更
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
import dynamic from 'next/dynamic';
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  Tooltip, 
  Legend 
} from 'recharts';

// グラフコンポーネントを動的にインポート（クライアントサイドのみ）
const TestRunChart = dynamic(
  () => import('@/components/molecules/TestRunChart'),
  {
    ssr: false,
    loading: () => (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }
);

export default function TestRunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  const runId = params.run_id as string;
  
  const { services } = useServices();
  const { testRuns, isLoading: isLoadingRuns } = useTestRuns(serviceId);
  const { testCases, isLoading: isLoadingTestCases } = useTestCases(serviceId);
  
  const testRun = React.useMemo(() => {
    if (!testRuns) return null;
    return testRuns.find(run => run.run_id === runId);
  }, [testRuns, runId]);

  // テストチェーンの詳細を取得
  const chainId = testRun?.suite_id; // chain_id を suite_id に変更
  const { testSuite, isLoading: isLoadingSuite } = useTestSuiteDetail(serviceId, chainId ?? null); // chainId を chainId ?? null に変更, testChain を testSuite に変更, useTestChain を useTestSuiteDetail に変更

  const [searchQuery, setSearchQuery] = React.useState('');
  
  const service = React.useMemo(() => {
    if (!services) return null;
    return services.find(p => p.id === serviceId);
  }, [services, serviceId]);
  
  // 検索フィルタリング
  const filteredResults = React.useMemo(() => {
    if (!testRun?.test_case_results || !testSuite?.test_cases) return []; // step_results を test_case_results に変更, testChain?.steps を testSuite?.test_cases に変更
    
    // TestRunのtest_case_resultsをTestCaseResult型として扱う
    return testRun.test_case_results.filter(caseResult => { // step_results を test_case_results に変更, result を caseResult に変更
      // TestCaseResult の case_id に対応する TestCase を取得
      const testCase = testSuite.test_cases?.find((testCase: TestCase) => testCase.id === caseResult.case_id); // testCase に型を指定
      if (!testCase) return false; // テストケース情報が見つからない場合はスキップ
      
      // 検索フィルター
      const lowerCaseQuery = searchQuery.toLowerCase();
      return (
        (testCase.name?.toLowerCase().includes(lowerCaseQuery)) || // testChainStep.name を testCase.name に変更
        (testCase.description?.toLowerCase().includes(lowerCaseQuery)) // testChainStep.path を testCase.description に変更 (パスではなく説明で検索)
      );
    });
  }, [testRun?.test_case_results, testSuite?.test_cases, searchQuery]); // testRun?.step_results を testRun?.test_case_results に変更, testChain?.steps を testSuite?.test_cases に変更
  
  // 円グラフデータの作成
  const pieChartData = React.useMemo(() => {
    if (!testRun?.test_case_results) return []; // step_results を test_case_results に変更
    
    const passedCount = testRun.test_case_results.filter(r => r.status === 'passed').length; // step_results を test_case_results に変更, passed を status === 'passed' に変更
    const failedCount = testRun.test_case_results.filter(r => r.status === 'failed').length; // step_results を test_case_results に変更, passed を status === 'failed' に変更
    const skippedCount = testRun.test_case_results.filter(r => r.status === 'skipped').length; // skippedCount を追加, step_results を test_case_results に変更, status === 'skipped' を追加
    
    return [
      { name: '成功', value: passedCount, color: '#10b981' },
      { name: '失敗', value: failedCount, color: '#ef4444' },
      { name: 'スキップ', value: skippedCount, color: '#9ca3af' }, // スキップを追加
    ].filter(item => item.value > 0);
  }, [testRun?.test_case_results]); // testRun?.step_results を testRun?.test_case_results に変更
  
  if (isLoadingRuns || isLoadingTestCases || isLoadingSuite) { // isLoadingChain を isLoadingSuite に変更
    return <div className="text-center py-8">読み込み中...</div>;
  }
  
  if (!service || !testRun) {
    return (
      <div className="text-center py-8">
        <p>テスト実行が見つかりません</p>
        <Button asChild className="mt-4">
          <Link href={`/services/${serviceId}/runs`}>テスト実行一覧に戻る</Link>
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
          <Link href={`/services/${serviceId}/runs`}>
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
                <dt className="font-medium">サービス</dt>
                <dd className="text-muted-foreground">{service.name}</dd>
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
                <dd className="text-muted-foreground">{testRun.test_case_results?.length || 0}</dd> {/* step_results を test_case_results に変更 */}
              </div>
              {testRun.status === 'completed' && (
                <div className="flex justify-between">
                  <dt className="font-medium">成功率</dt>
                  <dd className="text-muted-foreground">
                    {testRun.test_case_results && testRun.test_case_results.length > 0 ? ( // step_results を test_case_results に変更
                      `${Math.round((testRun.test_case_results.filter(r => r.status === 'passed').length / testRun.test_case_results.length) * 100)}%` // step_results を test_case_results に変更, passed を status === 'passed' に変更
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
                {filteredResults.map((caseResult) => { // result を caseResult に変更
                  // TestCaseResult の case_id に対応する TestCase を取得
                  const testCase = testSuite?.test_cases?.find((testCase: TestCase) => testCase.id === caseResult.case_id); // testCase に型を指定
                  if (!testCase) return null; // テストケース情報が見つからない場合はスキップ
                  
                  return (
                    <TableRow key={caseResult.id}> {/* result.id を caseResult.id に変更 */}
                      <TableCell>
                        {caseResult.status === 'passed' ? ( // result.passed を caseResult.status === 'passed' に変更
                          <CheckCircleIcon className="h-5 w-5 text-green-500" />
                        ) : (
                          <XCircleIcon className="h-5 w-5 text-red-500" />
                        )}
                      </TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          testCase.target_method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200' : // testChainStep.method を testCase.target_method に変更
                          testCase.target_method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200' : // testChainStep.method を testCase.target_method に変更
                          testCase.target_method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200' : // testChainStep.method を testCase.target_method に変更
                          testCase.target_method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200' : // testChainStep.method を testCase.target_method に変更
                          'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200'
                        }`}>
                          {testCase.target_method} {/* testChainStep.method を testCase.target_method に変更 */}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        <div className="flex flex-col">
                          <span>{testCase.target_path}</span> {/* testChainStep.path を testCase.target_path に変更 */}
                          <span className="text-xs text-muted-foreground truncate max-w-[300px]">
                            {testCase.name || '名前なし'} {/* TestChainStep.name を testCase.name に変更 */}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className={caseResult.status === 'passed' ? 'text-green-500' : 'text-red-500'}> {/* result.passed を caseResult.status === 'passed' に変更 */}
                          {caseResult.status} {/* result.status_code を caseResult.status に変更 */}
                        </span>
                      </TableCell>
                      <TableCell>
                        {/* テストケースレベルではレスポンス時間はないので表示しない */}
                        <span className="text-muted-foreground">-</span>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            const dialog = document.getElementById(`result-dialog-${caseResult.id}`); // result.id を caseResult.id に変更
                            if (dialog instanceof HTMLDialogElement) {
                              dialog.showModal();
                            }
                          }}
                        >
                          詳細
                        </Button>
                        
                        <dialog
                          id={`result-dialog-${caseResult.id}`} // result.id を caseResult.id に変更
                          className="p-0 rounded-lg shadow-lg backdrop:bg-black/50 w-full max-w-3xl"
                        >
                          <div className="p-6">
                            <div className="flex justify-between items-center mb-4">
                              <h3 className="text-lg font-semibold">テスト結果詳細</h3>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const dialog = document.getElementById(`result-dialog-${caseResult.id}`); // result.id を caseResult.id に変更
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
                                <span className="font-medium">テストケース名</span> {/* ステップ名からテストケース名に変更 */}
                                <span>{testCase.name || '名前なし'}</span> {/* testChainStep.name を testCase.name に変更 */}
                              </div>
                              <div className="flex justify-between">
                                <span className="font-medium">ステータス</span> {/* メソッドからステータスに変更 */}
                                <span className={caseResult.status === 'passed' ? 'text-green-500' : 'text-red-500'}> {/* testCase.target_method を caseResult.status === 'passed' ? 'text-green-500' : 'text-red-500' に変更 */}
                                  {caseResult.status} {/* testCase.target_method を caseResult.status に変更 */}
                                </span>
                              </div>
                              {caseResult.error_message && ( // error_message を追加
                                <div className="flex justify-between">
                                  <span className="font-medium">エラーメッセージ</span>
                                  <span className="text-red-500">{caseResult.error_message}</span>
                                </div>
                              )}
                              {/* ステップごとの結果を表示 */}
                              {caseResult.step_results?.map(stepResult => (
                                <div key={stepResult.id} className="border-t pt-4 mt-4 space-y-2">
                                  <h4 className="font-semibold">ステップ {stepResult.sequence}: {stepResult.method} {stepResult.path}</h4>
                                  <div className="grid grid-cols-2 gap-2 text-sm">
                                    <div className="flex justify-between">
                                      <span className="font-medium">結果:</span>
                                      <span className={stepResult.passed ? 'text-green-500' : 'text-red-500'}>
                                        {stepResult.passed ? '成功' : '失敗'}
                                      </span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className="font-medium">ステータスコード:</span>
                                      <span>{stepResult.status_code}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className="font-medium">レスポンス時間:</span>
                                      <span>{stepResult.response_time !== undefined ? `${stepResult.response_time.toFixed(2)} ms` : 'N/A'}</span>
                                    </div>
                                  </div>
                                  
                                  {stepResult.error_message && (
                                    <div className="space-y-1">
                                      <span className="font-medium text-red-500">エラーメッセージ:</span>
                                      <div className="bg-muted p-2 rounded-md overflow-auto max-h-24 text-red-500">
                                        <pre className="font-mono text-sm whitespace-pre-wrap">{stepResult.error_message}</pre>
                                      </div>
                                    </div>
                                  )}

                                  {stepResult.extracted_values && Object.keys(stepResult.extracted_values).length > 0 && (
                                    <div className="space-y-1">
                                      <span className="font-medium">抽出された値:</span>
                                      <div className="bg-muted p-2 rounded-md overflow-auto max-h-24">
                                        <pre className="font-mono text-sm whitespace-pre-wrap">{formatJSON(stepResult.extracted_values)}</pre>
                                      </div>
                                    </div>
                                  )}

                                  <Tabs defaultValue="response" className="mt-2">
                                    <TabsList className="grid w-full grid-cols-2">
                                      <TabsTrigger value="request">リクエスト</TabsTrigger>
                                      <TabsTrigger value="response">レスポンス</TabsTrigger>
                                    </TabsList>
                                    <TabsContent value="request" className="mt-2">
                                      <div className="bg-muted p-4 rounded-md overflow-auto max-h-60">
                                        <pre className="font-mono text-sm whitespace-pre-wrap">
                                          {stepResult.request_body ? formatJSON(stepResult.request_body) : 'リクエストボディなし'}
                                        </pre>
                                      </div>
                                    </TabsContent>
                                    <TabsContent value="response" className="mt-2">
                                      <div className="bg-muted p-4 rounded-md overflow-auto max-h-60">
                                        <pre className="font-mono text-sm whitespace-pre-wrap">
                                          {stepResult.response_body ? formatJSON(stepResult.response_body) : 'レスポンスボディなし'}
                                        </pre>
                                      </div>
                                    </TabsContent>
                                  </Tabs>
                                </div>
                              ))}
                            </div>
                            
                            {/* テストケースレベルのエラーメッセージはステップ結果の下に表示 */}
                            {caseResult.error_message && (
                              <div className="mt-4 space-y-1">
                                <span className="font-medium text-red-500">テストケースエラー:</span>
                                <div className="bg-muted p-2 rounded-md overflow-auto max-h-24 text-red-500">
                                  <pre className="font-mono text-sm whitespace-pre-wrap">{caseResult.error_message}</pre>
                                </div>
                              </div>
                            )}

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
