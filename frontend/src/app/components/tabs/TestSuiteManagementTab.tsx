"use client"

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetClose,
} from '@/components/ui/sheet';
import {
  PlayIcon,
  SearchIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  XIcon,
  Trash2Icon
} from 'lucide-react';
import { useTestSuites, useTestSuiteDetail, TestSuite } from '@/hooks/useTestChains'; // TestSuite 型をインポート
import { useTestRuns, TestRun, TestCase, TestStep } from '@/hooks/useTestRuns'; // TestRun, TestCase, TestStep 型をインポート
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';
import { toast } from 'sonner';
import { cn } from '@/lib/utils'; // cn 関数をインポート

export const TestChainManagementTab = ({ serviceId, service }: { serviceId: string, service: any }) => {
  const router = useRouter();
  const { testSuites, isLoading: isLoadingTestSuites, deleteTestSuite } = useTestSuites(serviceId);
  const { testRuns, isLoading: isLoadingTestRuns } = useTestRuns(serviceId);

  // テスト生成関連のstateは削除
  // const [isGenerating, setIsGenerating] = React.useState(false);
  // const [generationStatus, setGenerationStatus] = React.useState<'idle' | 'generating' | 'completed' | 'failed'>('idle');
  // const [generatedCount, setGeneratedCount] = React.useState(0);
  // const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  // テストスイート詳細関連のstate
  const [selectedSuiteId, setSelectedSuiteId] = React.useState<string | null>(null);
  const [isDetailOpen, setIsDetailOpen] = React.useState(false);
  const { testSuite, isLoading: isLoadingSuiteDetail } = useTestSuiteDetail(serviceId, selectedSuiteId);

  // 削除確認ダイアログ関連のstate
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false);
  const [suiteToDelete, setSuiteToDelete] = React.useState<string | null>(null);

  // テスト実行関連のstate
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedSuites, setSelectedSuites] = React.useState<string[]>([]);
  const [isRunning, setIsRunning] = React.useState(false);

  // 検索フィルタリング（メモ化）
  const filteredSuites = React.useMemo(() => {
    if (!testSuites) return [];

    if (!searchQuery) return testSuites;

    const query = searchQuery.toLowerCase();
    return testSuites.filter((suite: TestSuite) =>
      suite.name.toLowerCase().includes(query) ||
      suite.description?.toLowerCase().includes(query) ||
      suite.test_cases?.some((testCase: TestCase) =>
        testCase.test_steps?.some((testStep: TestStep) =>
          testStep.method.toLowerCase().includes(query) ||
          testStep.path.toLowerCase().includes(query)
        )
      )
    );
  }, [testSuites, searchQuery]);

  // すべて選択/解除
  const toggleSelectAll = () => {
    if (selectedSuites.length === filteredSuites.length) {
      setSelectedSuites([]);
    } else {
      setSelectedSuites(filteredSuites.map(ts => ts.id));
    }
  };

  // 個別のテストスイート選択/解除
  const toggleTestSuite = (id: string) => {
    setSelectedSuites(prevSelected =>
      prevSelected.includes(id)
        ? prevSelected.filter(suiteId => suiteId !== id)
        : [...prevSelected, id]
    );
  };

  // テスト生成を開始 (削除)
  // const handleGenerateTests = async () => { ... };

  // テスト実行
  const handleRunTests = async () => {
    if (selectedSuites.length === 0) {
      toast.error('テストスイートが選択されていません');
      return;
    }

    try {
      setIsRunning(true);

      const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
      const response = await fetch(`${API}/api/services/${serviceId}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          suite_ids: selectedSuites,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'テスト実行に失敗しました');
      }

      const data = await response.json();

      toast.success('テスト実行が開始されました', {
        description: `実行ID: ${data.run_id}`,
      });

      // テスト実行詳細ページにリダイレクト
      router.push(`/services/${serviceId}/runs/${data.run_id}`);
    } catch (error) {
      console.error('テスト実行エラー:', error);

      toast.error('エラーが発生しました', {
        description: error instanceof Error ? error.message : '不明なエラーが発生しました',
      });
    } finally {
      setIsRunning(false);
    }
  };


  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>テストスイート管理・実行</CardTitle>
          <CardDescription>
            生成されたテストスイートの一覧です。実行したいスイートを選択して実行ボタンを押してください。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col md:flex-row gap-4 items-end">
            {/* テストスイート一覧へのリンクを追加 */}
            <Button variant="outline" size="sm" asChild>
              <Link href={`/services/${serviceId}/test-suites`}>
                テストスイート一覧
              </Link>
            </Button>
            <div className="relative flex-1"> {/* 検索バー */}
              <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="テストスイートを検索..."
                className="pl-8"
                value={searchQuery}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2"> {/* すべて選択チェックボックス */}
              <Checkbox
                id="select-all"
                checked={filteredSuites.length > 0 && selectedSuites.length === filteredSuites.length}
                onCheckedChange={toggleSelectAll}
              />
              <label htmlFor="select-all" className="text-sm">すべて選択</label>
            </div>
            {/* テストチェーン生成ボタンは削除 */}
            {/* <Button onClick={handleGenerateTests} disabled={isGenerating}>
              <FileTextIcon className="h-4 w-4 mr-2" />
              {isGenerating ? 'テスト生成中...' : 'テストチェーン生成'}
            </Button> */}
          </div>

          {/* テスト生成ステータス表示は削除 */}
          {/* {generationStatus === 'generating' && (
            <div className="text-center p-6 space-y-4 mb-4 bg-muted rounded-lg">
              <div className="flex justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
              </div>
              <p className="font-medium">テストチェーン生成中...</p>
              <p className="text-sm text-muted-foreground">
                OpenAPIスキーマを解析して依存関係を抽出し、テストチェーンを生成しています。
                <br />
                この処理には数分かかる場合があります。
              </p>
            </div>
          )} */}

          {/* {generationStatus === 'completed' && (
            <div className="text-center p-6 space-y-4 mb-4 bg-green-50 dark:bg-green-950 rounded-lg">
              <div className="flex justify-center">
                <CheckCircleIcon className="h-12 w-12 text-green-500" />
              </div>
              <p className="font-medium">テストチェーン生成が完了しました</p>
              <p className="text-sm">
                {generatedCount}件のテストチェーンが生成されました。
              </p>
            </div>
          )} */}

          {/* {generationStatus === 'failed' && (
            <div className="text-center p-6 space-y-4 mb-4 bg-red-50 dark:bg-red-950 rounded-lg">
              <div className="flex justify-center">
                <XCircleIcon className="h-12 w-12 text-red-500" />
              </div>
              <p className="font-medium">テストチェーン生成に失敗しました</p>
              <p className="text-sm text-muted-foreground">
                エラーが発生したため、テストチェーン生成を完了できませんでした。
                <br />
                {errorMessage ? (
                  <span className="font-mono text-red-600 block mt-2 p-2 bg-red-100 dark:bg-red-900 rounded">
                    エラー: {errorMessage}
                  </span>
                ) : (
                  'もう一度お試しいただくか、スキーマを確認してください。'
                )}
              </p>
              <div className="flex flex-col gap-2 items-center">
                <Button onClick={handleGenerateTests}>
                  再試行
                </Button>
              </div>
            </div>
          )} */}

          {isLoadingTestSuites ? (
            <div className="text-center py-6 md:py-8">読み込み中...</div>
          ) : filteredSuites && filteredSuites.length > 0 ? (
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]"></TableHead> {/* チェックボックス用の列を追加 */}
                    <TableHead className="w-[300px]">スイート名</TableHead>
                    <TableHead className="w-[200px]">対象エンドポイント</TableHead>
                    <TableHead className="w-[100px]">ケース数</TableHead>
                    <TableHead className="w-[100px]">アクション</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredSuites.map((suite: TestSuite) => (
                    <TableRow
                      key={suite.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => {
                        setSelectedSuiteId(suite.id);
                        setIsDetailOpen(true);
                      }}
                    >
                      <TableCell onClick={(e) => e.stopPropagation()}> {/* チェックボックス列 */}
                        <Checkbox
                          checked={selectedSuites.includes(suite.id)}
                          onCheckedChange={() => toggleTestSuite(suite.id)}
                        />
                      </TableCell>
                      <TableCell className="font-medium">{suite.name}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {suite.target_method && suite.target_path && (
                          <div className="flex items-center gap-2">
                            <span className={cn(
                              'px-2.5 py-0.5 text-xs font-semibold rounded-full',
                              suite.target_method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                              suite.target_method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                              suite.target_method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                              suite.target_method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                              'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                            )}>
                              {suite.target_method}
                            </span>
                            <span>{suite.target_path}</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>{suite.test_cases_count || 0} ケース</TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()} className="flex space-x-2">
                        {/* 個別の実行ボタンは削除し、一括実行ボタンを使用 */}
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => {
                            setSuiteToDelete(suite.id);
                            setShowDeleteDialog(true);
                          }}
                        >
                          <Trash2Icon className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8 border rounded-lg bg-background">
              <p className="text-muted-foreground">テストスイートがありません</p>
              {searchQuery ? (
                <p className="mt-2">検索条件を変更してください</p>
              ) : (
                <p className="mt-2">テストスイート生成はエンドポイント管理タブから実行してください。</p>
              )}
            </div>
          )}

          {/* 選択したスイートの実行ボタン */}
          {filteredSuites.length > 0 && (
            <div className="flex justify-end">
              <Button
                onClick={handleRunTests}
                disabled={isRunning || selectedSuites.length === 0}
              >
                <PlayIcon className="h-4 w-4 mr-2" />
                {isRunning ? 'テスト実行中...' : `選択したスイートを実行 (${selectedSuites.length}件)`}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 最近のテスト実行 */}
      <Card>
        <CardHeader>
          <CardTitle>最近のテスト実行</CardTitle>
          <CardDescription>
            <Link href={`/services/${serviceId}/runs`} className="text-sm hover:underline">
              すべて表示
            </Link>
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingTestRuns ? (
            <div className="text-center py-4">読み込み中...</div>
          ) : testRuns && testRuns.length > 0 ? (
            <div className="space-y-2">
              {testRuns.slice(0, 5).map((run: TestRun) => (
                <Link
                  key={run.id}
                  href={`/services/${serviceId}/runs/${run.run_id}`}
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


      {/* 削除確認ダイアログ */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>テストスイートを削除しますか？</AlertDialogTitle>
          </AlertDialogHeader>
          <AlertDialogDescription>
            この操作は元に戻せません。テストスイートに関連する全てのデータ（実行結果など）が完全に削除されます。
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (suiteToDelete) {
                   await deleteTestSuite(suiteToDelete);
                   setSuiteToDelete(null);
                   setShowDeleteDialog(false);
                }
              }}
            >
              削除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* テストスイート詳細表示用のサイドパネル */}
      <Sheet open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
          <SheetHeader className="mb-6 pb-4 border-b">
            <div className="flex items-center justify-between">
              <SheetTitle className="text-xl font-bold">テストスイート詳細</SheetTitle>
              <SheetClose className="rounded-full hover:bg-muted p-2 transition-colors">
                <XIcon className="h-4 w-4" />
              </SheetClose>
            </div>
            <SheetDescription>
              {testSuite && (
                <div className="mt-2">
                  <h3 className="text-lg font-semibold">{testSuite.name}</h3>
                  {testSuite.description && (
                    <p className="text-sm text-muted-foreground mt-1">{testSuite.description}</p>
                  )}
                </div>
              )}
            </SheetDescription>
          </SheetHeader>

          {isLoadingSuiteDetail ? (
            <div className="flex justify-center items-center h-40">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          ) : testSuite ? (
            <div className="space-y-8">
              {/* テストケース一覧 */}
              <div className="bg-card rounded-lg p-4 shadow-sm">
                <h3 className="text-lg font-semibold mb-3 text-primary">テストケース</h3>
                <div className="space-y-4">
                  {testSuite.test_cases && testSuite.test_cases.map((testCase: TestCase, index: number) => (
                    <div key={index} className="border rounded-md p-4 hover:bg-muted/20 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {/* テストケースの概要表示 */}
                          <span className={cn(
                            'px-2 py-1 rounded text-xs font-medium',
                            testCase.target_method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                            testCase.target_method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                            testCase.target_method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                            testCase.target_method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                            'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
                          )}>
                            {testCase.target_method}
                          </span>
                          <span className="font-mono text-sm">{testCase.target_path}</span>
                        </div>
                        <span className="text-xs text-muted-foreground">ケース {index + 1}</span>
                      </div>

                      {testCase.name && (
                        <p className="text-sm font-medium mb-2">{testCase.name}</p>
                      )}
                       {testCase.description && (
                        <p className="text-sm text-muted-foreground mt-1">{testCase.description}</p>
                      )}


                      {/* テストステップ一覧 */}
                      <div className="mt-3 space-y-3">
                        <h4 className="text-sm font-semibold mb-2">テストステップ:</h4>
                        {testCase.test_steps && testCase.test_steps.map((testStep: TestStep, stepIndex: number) => (
                          <div key={testStep.id} className="border rounded-md p-4 hover:bg-muted/20 transition-colors ml-4">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className={cn(
                                  'px-2 py-1 rounded text-xs font-medium',
                                  testStep.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                                  testStep.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                                  testStep.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                                  testStep.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                                  'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
                                )}>
                                  {testStep.method}
                                </span>
                                <span className="font-mono text-sm">{testStep.path}</span>
                              </div>
                              <span className="text-xs text-muted-foreground">ステップ {testStep.sequence}</span>
                            </div>

                            {testStep.name && (
                              <p className="text-sm font-medium mb-2">{testStep.name}</p>
                            )}

                            {/* リクエストヘッダー */}
                            {testStep.request_headers && Object.keys(testStep.request_headers).length > 0 && (
                              <div className="mb-2">
                                <h4 className="text-sm font-medium mb-1">リクエストヘッダー:</h4>
                                <div className="bg-muted/30 p-2 rounded-md overflow-auto border">
                                  <pre className="text-xs whitespace-pre-wrap font-mono">
                                    {JSON.stringify(testStep.request_headers, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}

                            {/* リクエストボディ */}
                            {testStep.request_body && (
                              <div className="mb-2">
                                <h4 className="text-sm font-medium mb-1">リクエストボディ:</h4>
                                <div className="bg-muted/30 p-2 rounded-md overflow-auto border">
                                  <pre className="text-xs whitespace-pre-wrap font-mono">
                                    {JSON.stringify(testStep.request_body, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}

                            {/* リクエストパラメータ */}
                            {testStep.request_params && Object.keys(testStep.request_params).length > 0 && (
                              <div className="mb-2">
                                <h4 className="text-sm font-medium mb-1">リクエストパラメータ:</h4>
                                <div className="bg-muted/30 p-2 rounded-md overflow-auto border">
                                  <pre className="text-xs whitespace-pre-wrap font-mono">
                                    {JSON.stringify(testStep.request_params, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}

                            {/* 期待されるステータスコード */}
                            {testStep.expected_status && (
                              <div className="mb-2">
                                <h4 className="text-sm font-medium mb-1">期待されるステータスコード:</h4>
                                <span className={cn(
                                  'px-2 py-1 rounded text-xs font-medium',
                                  testStep.expected_status >= 200 && testStep.expected_status < 300 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                                  testStep.expected_status >= 400 && testStep.expected_status < 500 ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300' :
                                  testStep.expected_status >= 500 ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                                  'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
                                )}>
                                  {testStep.expected_status}
                                </span>
                              </div>
                            )}

                            {/* 抽出ルール */}
                            {testStep.extract_rules && Object.keys(testStep.extract_rules).length > 0 && (
                              <div className="mb-2">
                                <h4 className="text-sm font-medium mb-1">抽出ルール:</h4>
                                <div className="bg-muted/30 p-2 rounded-md overflow-auto border">
                                  <pre className="text-xs whitespace-pre-wrap font-mono">
                                    {JSON.stringify(testStep.extract_rules, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-muted-foreground">テストスイートの詳細を取得できませんでした</p>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default TestChainManagementTab;
