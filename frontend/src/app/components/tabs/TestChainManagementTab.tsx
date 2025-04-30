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
} from 'lucide-react'; // FileTextIcon は不要になったので削除
import { useTestChains, useTestChainDetail } from '@/hooks/useTestChains';
import { useChainRuns } from '@/hooks/useTestRuns';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';
import { toast } from 'sonner';

export const TestChainManagementTab = ({ projectId, project }: { projectId: string, project: any }) => {
  const router = useRouter();
  const { testChains, isLoading: isLoadingTestChains, deleteChain } = useTestChains(projectId);
  const { chainRuns, isLoading: isLoadingChainRuns } = useChainRuns(projectId);

  // テスト生成関連のstateは削除
  // const [isGenerating, setIsGenerating] = React.useState(false);
  // const [generationStatus, setGenerationStatus] = React.useState<'idle' | 'generating' | 'completed' | 'failed'>('idle');
  // const [generatedCount, setGeneratedCount] = React.useState(0);
  // const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  // テストチェーン詳細関連のstate
  const [selectedChainId, setSelectedChainId] = React.useState<string | null>(null);
  const [isDetailOpen, setIsDetailOpen] = React.useState(false);
  const { testChain, isLoading: isLoadingChainDetail } = useTestChainDetail(projectId, selectedChainId);

  // 削除確認ダイアログ関連のstate
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false);
  const [chainToDelete, setChainToDelete] = React.useState<string | null>(null);

  // テスト実行関連のstate
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedChains, setSelectedChains] = React.useState<string[]>([]);
  const [isRunning, setIsRunning] = React.useState(false);

  // 検索フィルタリング（メモ化）
  const filteredChains = React.useMemo(() => {
    if (!testChains) return [];

    if (!searchQuery) return testChains;

    const query = searchQuery.toLowerCase();
    return testChains.filter(chain =>
      chain.name.toLowerCase().includes(query) ||
      chain.description?.toLowerCase().includes(query) ||
      chain.steps?.some((step: any) =>
        step.path.toLowerCase().includes(query) ||
        step.method.toLowerCase().includes(query)
      )
    );
  }, [testChains, searchQuery]);

  // すべて選択/解除
  const toggleSelectAll = () => {
    if (selectedChains.length === filteredChains.length) {
      setSelectedChains([]);
    } else {
      setSelectedChains(filteredChains.map(tc => tc.id));
    }
  };

  // 個別のテストチェーン選択/解除
  const toggleTestChain = (id: string) => {
    if (selectedChains.includes(id)) {
      setSelectedChains(selectedChains.filter(tcId => tcId !== id));
    } else {
      setSelectedChains([...selectedChains, id]);
    }
  };

  // テスト生成を開始 (削除)
  // const handleGenerateTests = async () => { ... };

  // テスト実行
  const handleRunTests = async () => {
    if (selectedChains.length === 0) {
      toast.error('テストチェーンが選択されていません');
      return;
    }

    try {
      setIsRunning(true);

      const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
      const response = await fetch(`${API}/api/projects/${projectId}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chain_ids: selectedChains,
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
      router.push(`/projects/${projectId}/runs/${data.run_id}`);
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
          <CardTitle>テストチェーン管理・実行</CardTitle> {/* タイトルを変更 */}
          <CardDescription>
            生成されたテストチェーンの一覧です。実行したいチェーンを選択して実行ボタンを押してください。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4"> {/* space-y-4を追加 */}
          <div className="flex flex-col md:flex-row gap-4 items-end"> {/* 検索バーと生成ボタンを横並びに */}
            <div className="relative flex-1"> {/* 検索バー */}
              <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="テストチェーンを検索..."
                className="pl-8"
                value={searchQuery}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2"> {/* すべて選択チェックボックス */}
              <Checkbox
                id="select-all"
                checked={filteredChains.length > 0 && selectedChains.length === filteredChains.length}
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

          {isLoadingTestChains ? (
            <div className="text-center py-6 md:py-8">読み込み中...</div>
          ) : filteredChains && filteredChains.length > 0 ? (
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]"></TableHead> {/* チェックボックス用の列を追加 */}
                    <TableHead className="w-[300px]">チェーン名</TableHead> {/* 幅を調整 */}
                    <TableHead className="w-[200px]">対象エンドポイント</TableHead> {/* 対象エンドポイント列を追加 */}
                    <TableHead className="w-[100px]">ステップ数</TableHead> {/* 幅を調整 */}
                    <TableHead className="w-[100px]">アクション</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredChains.map((chain) => (
                    <TableRow
                      key={chain.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => {
                        setSelectedChainId(chain.id);
                        setIsDetailOpen(true);
                      }}
                    >
                      <TableCell onClick={(e) => e.stopPropagation()}> {/* チェックボックス列 */}
                        <Checkbox
                          checked={selectedChains.includes(chain.id)}
                          onCheckedChange={() => toggleTestChain(chain.id)}
                        />
                      </TableCell>
                      <TableCell className="font-medium">{chain.name}</TableCell>
                      <TableCell className="font-mono text-sm"> {/* 対象エンドポイント列 */}
                        {chain.last_step_method && chain.last_step_path && (
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              chain.last_step_method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                              chain.last_step_method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                              chain.last_step_method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                              chain.last_step_method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                              'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
                            }`}>
                              {chain.last_step_method}
                            </span>
                            <span>{chain.last_step_path}</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>{chain.steps_count || 0} ステップ</TableCell> {/* ステップ数 */}
                      <TableCell onClick={(e) => e.stopPropagation()} className="flex space-x-2">
                        {/* 個別の実行ボタンは削除し、一括実行ボタンを使用 */}
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => {
                            setChainToDelete(chain.id);
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
              <p className="text-muted-foreground">テストチェーンがありません</p>
              {searchQuery ? (
                <p className="mt-2">検索条件を変更してください</p>
              ) : (
                <p className="mt-2">テストチェーン生成はエンドポイント管理タブから実行してください。</p>
              )}
            </div>
          )}

          {/* 選択したチェーンの実行ボタン */}
          {filteredChains.length > 0 && (
            <div className="flex justify-end">
              <Button
                onClick={handleRunTests}
                disabled={isRunning || selectedChains.length === 0}
              >
                <PlayIcon className="h-4 w-4 mr-2" />
                {isRunning ? 'テスト実行中...' : `選択したチェーンを実行 (${selectedChains.length}件)`}
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


      {/* 削除確認ダイアログ */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>テストチェーンを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は元に戻せません。テストチェーンに関連する全てのデータ（実行結果など）が完全に削除されます。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (chainToDelete) {
                  await deleteChain(chainToDelete);
                  setChainToDelete(null);
                  setShowDeleteDialog(false);
                }
              }}
            >
              削除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* テストチェーン詳細表示用のサイドパネル */}
      <Sheet open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
          <SheetHeader className="mb-6 pb-4 border-b">
            <div className="flex items-center justify-between">
              <SheetTitle className="text-xl font-bold">テストチェーン詳細</SheetTitle>
              <SheetClose className="rounded-full hover:bg-muted p-2 transition-colors">
                <XIcon className="h-4 w-4" />
              </SheetClose>
            </div>
            <SheetDescription>
              {testChain && (
                <div className="mt-2">
                  <h3 className="text-lg font-semibold">{testChain.name}</h3>
                  {testChain.description && (
                    <p className="text-sm text-muted-foreground mt-1">{testChain.description}</p>
                  )}
                </div>
              )}
            </SheetDescription>
          </SheetHeader>

          {isLoadingChainDetail ? (
            <div className="flex justify-center items-center h-40">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          ) : testChain ? (
            <div className="space-y-8">
              {/* ステップ一覧 */}
              <div className="bg-card rounded-lg p-4 shadow-sm">
                <h3 className="text-lg font-semibold mb-3 text-primary">テストステップ</h3>
                <div className="space-y-4">
                  {testChain.steps && testChain.steps.map((step, index) => (
                    <div key={index} className="border rounded-md p-4 hover:bg-muted/20 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            step.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                            step.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                            step.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                            step.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                            'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
                          }`}>
                            {step.method}
                          </span>
                          <span className="font-mono text-sm">{step.path}</span>
                        </div>
                        <span className="text-xs text-muted-foreground">ステップ {index + 1}</span>
                      </div>

                      {step.name && (
                        <p className="text-sm font-medium mb-2">{step.name}</p>
                      )}

                      {/* リクエスト情報 */}
                      <div className="mt-3 space-y-3">
                        {/* リクエストヘッダー */}
                        {step.request && step.request.headers && Object.keys(step.request.headers).length > 0 && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">リクエストヘッダー:</h4>
                            <div className="bg-muted/30 p-2 rounded-md overflow-auto border">
                              <pre className="text-xs whitespace-pre-wrap font-mono">
                                {JSON.stringify(step.request.headers, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}

                        {/* リクエストボディ */}
                        {step.request && step.request.body && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">リクエストボディ:</h4>
                            <div className="bg-muted/30 p-2 rounded-md overflow-auto border">
                              <pre className="text-xs whitespace-pre-wrap font-mono">
                                {JSON.stringify(step.request.body, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}

                        {/* リクエストパラメータ */}
                        {step.request && step.request.params && Object.keys(step.request.params).length > 0 && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">リクエストパラメータ:</h4>
                            <div className="bg-muted/30 p-2 rounded-md overflow-auto border">
                              <pre className="text-xs whitespace-pre-wrap font-mono">
                                {JSON.stringify(step.request.params, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}

                        {/* 期待されるステータスコード */}
                        {step.expected_status && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">期待されるステータスコード:</h4>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              step.expected_status >= 200 && step.expected_status < 300 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                              step.expected_status >= 400 && step.expected_status < 500 ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300' :
                              step.expected_status >= 500 ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                              'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
                            }`}>
                              {step.expected_status}
                            </span>
                          </div>
                        )}

                        {/* 抽出ルール */}
                        {step.extract_rules && Object.keys(step.extract_rules).length > 0 && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">抽出ルール:</h4>
                            <div className="bg-muted/30 p-2 rounded-md overflow-auto border">
                              <pre className="text-xs whitespace-pre-wrap font-mono">
                                {JSON.stringify(step.extract_rules, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-muted-foreground">テストチェーンの詳細を取得できませんでした</p>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default TestChainManagementTab;