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
  PlayIcon, 
  SearchIcon, 
  CheckCircleIcon, 
  XCircleIcon, 
  ClockIcon 
} from 'lucide-react';
import { useTestChains } from '@/hooks/useTestChains';
import { useChainRuns } from '@/hooks/useTestRuns';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';
import { toast } from 'sonner';

export const TestExecutionTab = ({ projectId, project }: { projectId: string, project: any }) => {
  const router = useRouter();
  const { testChains, isLoading } = useTestChains(projectId);
  const { chainRuns, isLoading: isLoadingChainRuns } = useChainRuns(projectId);
  
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
          <CardTitle>テストチェーン実行</CardTitle>
          <CardDescription>
            実行するテストチェーンを選択してください。各チェーンは複数のAPIリクエストステップで構成されています。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="relative flex-1">
              <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="テストチェーンを検索..."
                className="pl-8"
                value={searchQuery}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="select-all"
                checked={filteredChains.length > 0 && selectedChains.length === filteredChains.length}
                onCheckedChange={toggleSelectAll}
              />
              <label htmlFor="select-all" className="text-sm">すべて選択</label>
            </div>
          </div>
          
          {isLoading ? (
            <div className="text-center py-8">読み込み中...</div>
          ) : filteredChains.length > 0 ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]"></TableHead>
                    <TableHead className="w-[300px]">チェーン名</TableHead>
                    <TableHead className="w-[150px]">メソッド順序</TableHead>
                    <TableHead>パス</TableHead>
                    <TableHead className="w-[100px]">ステップ数</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredChains.map((chain) => (
                    <TableRow key={chain.id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedChains.includes(chain.id)}
                          onCheckedChange={() => toggleTestChain(chain.id)}
                        />
                      </TableCell>
                      <TableCell className="font-medium">{chain.name}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          {chain.steps && chain.steps.map((step: any, index: number) => (
                            <span key={index} className={`px-2 py-1 rounded text-xs font-medium ${
                              step.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                              step.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                              step.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                              step.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                              'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
                            }`}>
                              {step.method}
                              {chain.steps && index < chain.steps.length - 1 && <span className="ml-1">→</span>}
                            </span>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {chain.steps && chain.steps.length > 0 && (
                          <div className="flex flex-col gap-1">
                            <span>{chain.steps[0].path}</span>
                            {chain.steps.length > 1 && (
                              <span className="text-muted-foreground">→ {chain.steps[chain.steps.length - 1].path}</span>
                            )}
                            {chain.steps.length > 2 && (
                              <span className="text-muted-foreground text-xs">+ {chain.steps.length - 2} more steps</span>
                            )}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>{chain.steps_count || chain.steps?.length || 0} ステップ</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8 border rounded-lg bg-background">
              <p className="text-muted-foreground">テストチェーンが見つかりません</p>
              {searchQuery ? (
                <p className="mt-2">検索条件を変更してください</p>
              ) : (
                <div className="mt-4">
                  <p className="mb-2">テストチェーンを生成してください</p>
                  <Button onClick={() => {
                    // テストチェーン管理タブに遷移
                    document.querySelector('[data-value="test-chains"]')?.dispatchEvent(
                      new MouseEvent('click', { bubbles: true })
                    );
                  }}>
                    テストチェーン生成
                  </Button>
                </div>
              )}
            </div>
          )}
          
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
    </div>
  );
};

export default TestExecutionTab;