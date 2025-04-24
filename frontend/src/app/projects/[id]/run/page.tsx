"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useProjects } from '../../../hooks/useProjects';
import { useTestChains, TestChain } from '../../../hooks/useTestChains';
import { Button } from '../../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../components/ui/card';
import { Checkbox } from '../../../components/ui/checkbox';
import { Input } from '../../../components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../../components/ui/table';
import { ArrowLeftIcon, SearchIcon, PlayIcon, CheckCircleIcon, XCircleIcon, ListIcon } from 'lucide-react';
import { toast } from 'sonner';

// メモ化されたテーブル行コンポーネント
const TestChainRow = React.memo(({
  testChain,
  isSelected,
  onToggle
}: {
  testChain: TestChain;
  isSelected: boolean;
  onToggle: () => void;
}) => {
  // チェーン内の最初のステップのメソッドとパスを取得
  const firstStep = testChain.steps[0];
  const lastStep = testChain.steps[testChain.steps.length - 1];
  
  return (
    <TableRow>
      <TableCell>
        <Checkbox
          checked={isSelected}
          onCheckedChange={onToggle}
        />
      </TableCell>
      <TableCell className="font-medium">
        {testChain.name}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1">
          {testChain.steps.map((step, index) => (
            <span key={index} className={`px-2 py-1 rounded text-xs font-medium ${
              step.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
              step.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
              step.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
              step.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
              'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
            }`}>
              {step.method}
              {index < testChain.steps.length - 1 && <span className="ml-1">→</span>}
            </span>
          ))}
        </div>
      </TableCell>
      <TableCell className="font-mono text-sm">
        <div className="flex flex-col gap-1">
          <span>{firstStep.path}</span>
          {testChain.steps.length > 1 && (
            <span className="text-muted-foreground">→ {lastStep.path}</span>
          )}
          {testChain.steps.length > 2 && (
            <span className="text-muted-foreground text-xs">+ {testChain.steps.length - 2} more steps</span>
          )}
        </div>
      </TableCell>
      <TableCell>{testChain.steps.length} ステップ</TableCell>
    </TableRow>
  );
});

export default function RunTestsPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = params.id as string;
  const chainIdFromUrl = searchParams.get('chain_id');
  
  const { projects, isLoading: isLoadingProjects } = useProjects();
  const project = React.useMemo(() => {
    if (!projects) return null;
    return projects.find(p => p.id === projectId);
  }, [projects, projectId]);
  const { testChains, isLoading } = useTestChains(projectId);
  
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
      chain.steps.some(step =>
        step.path.toLowerCase().includes(query) ||
        step.method.toLowerCase().includes(query)
      )
    );
  }, [testChains, searchQuery]);
  
  // URLからチェーンIDが指定されていた場合、そのチェーンを選択
  React.useEffect(() => {
    if (chainIdFromUrl && testChains) {
      const chain = testChains.find(tc => tc.chain_id === chainIdFromUrl);
      if (chain) {
        setSelectedChains([chain.id]);
      }
    }
  }, [chainIdFromUrl, testChains]);
  
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
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/projects/${projectId}`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            プロジェクト詳細に戻る
          </Link>
        </Button>
      </div>
      
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">テストチェーン実行</h1>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>テストチェーン選択</CardTitle>
          <CardDescription>
            実行するテストチェーンを選択してください。各チェーンは複数のAPIリクエストステップで構成されています。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 p-4 bg-muted rounded-lg">
            <div className="flex-1">
              <h3 className="font-semibold">{project.name}</h3>
              <p className="text-sm text-muted-foreground">
                {project.description || 'プロジェクトの説明はありません'}
              </p>
            </div>
            <Button
              onClick={handleRunTests}
              disabled={isRunning || selectedChains.length === 0}
            >
              <PlayIcon className="h-4 w-4 mr-2" />
              {isRunning ? 'テスト実行中...' : 'チェーン実行'}
            </Button>
          </div>
          
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
                    <TestChainRow
                      key={chain.id}
                      testChain={chain}
                      isSelected={selectedChains.includes(chain.id)}
                      onToggle={() => toggleTestChain(chain.id)}
                    />
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
                  <Button asChild>
                    <Link href={`/projects/${projectId}/generate`}>
                      テストチェーン生成
                    </Link>
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
    </div>
  );
}