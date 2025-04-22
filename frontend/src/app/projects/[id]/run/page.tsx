"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
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
import { ArrowLeftIcon, SearchIcon, PlayIcon, CheckCircleIcon, XCircleIcon } from 'lucide-react';
import { toast } from 'sonner';

// 型定義
interface Project {
  id: string;
  name: string;
  description?: string;
}

interface TestCase {
  id: string;
  case_id: string;
  title: string;
  method: string;
  path: string;
  expected_status: number;
}

// プロジェクト情報を取得するカスタムフック
function useProject(projectId: string) {
  const [project, setProject] = React.useState<Project | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    if (!projectId) return;

    async function fetchProject() {
      try {
        setIsLoading(true);
        const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
        const response = await fetch(`${API}/api/projects/${projectId}`);
        
        if (!response.ok) {
          throw new Error(`API ${response.status}`);
        }
        
        const data = await response.json();
        setProject(data);
      } catch (err) {
        console.error('プロジェクト情報の取得に失敗しました:', err);
        setError(err instanceof Error ? err : new Error('不明なエラー'));
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchProject();
  }, [projectId]);
  
  return { project, isLoading, error };
}

// テストケース一覧を取得するカスタムフック
function useTestCases(projectId: string) {
  const [testCases, setTestCases] = React.useState<TestCase[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    if (!projectId) return;

    async function fetchTestCases() {
      try {
        setIsLoading(true);
        const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
        const response = await fetch(`${API}/api/projects/${projectId}/tests`);
        
        if (!response.ok) {
          throw new Error(`API ${response.status}`);
        }
        
        const data = await response.json();
        setTestCases(data);
      } catch (err) {
        console.error('テストケース一覧の取得に失敗しました:', err);
        setError(err instanceof Error ? err : new Error('不明なエラー'));
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchTestCases();
  }, [projectId]);
  
  return { testCases, isLoading, error };
}

// メモ化されたテーブル行コンポーネント
const TestCaseRow = React.memo(({
  testCase,
  isSelected,
  onToggle
}: {
  testCase: TestCase;
  isSelected: boolean;
  onToggle: () => void;
}) => {
  return (
    <TableRow>
      <TableCell>
        <Checkbox
          checked={isSelected}
          onCheckedChange={onToggle}
        />
      </TableCell>
      <TableCell className="font-medium">
        {testCase.title}
      </TableCell>
      <TableCell>
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          testCase.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
          testCase.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
          testCase.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
          testCase.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
          'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
        }`}>
          {testCase.method}
        </span>
      </TableCell>
      <TableCell className="font-mono text-sm">{testCase.path}</TableCell>
      <TableCell>{testCase.expected_status}</TableCell>
    </TableRow>
  );
});

export default function RunTestsPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = params.id as string;
  const caseIdFromUrl = searchParams.get('case_id');
  
  const { project, isLoading: isLoadingProject } = useProject(projectId);
  const { testCases, isLoading } = useTestCases(projectId);
  
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedTestCases, setSelectedTestCases] = React.useState<string[]>([]);
  const [isRunning, setIsRunning] = React.useState(false);
  
  // 検索フィルタリング（メモ化）
  const filteredTestCases = React.useMemo(() => {
    if (!testCases) return [];
    
    if (!searchQuery) return testCases;
    
    const query = searchQuery.toLowerCase();
    return testCases.filter(testCase =>
      testCase.title.toLowerCase().includes(query) ||
      testCase.path.toLowerCase().includes(query) ||
      testCase.method.toLowerCase().includes(query)
    );
  }, [testCases, searchQuery]);
  
  // URLからテストケースIDが指定されていた場合、そのテストケースを選択
  React.useEffect(() => {
    if (caseIdFromUrl && testCases) {
      const testCase = testCases.find(tc => tc.case_id === caseIdFromUrl);
      if (testCase) {
        setSelectedTestCases([testCase.id]);
      }
    }
  }, [caseIdFromUrl, testCases]);
  
  // すべて選択/解除
  const toggleSelectAll = () => {
    if (selectedTestCases.length === filteredTestCases.length) {
      setSelectedTestCases([]);
    } else {
      setSelectedTestCases(filteredTestCases.map(tc => tc.id));
    }
  };
  
  // 個別のテストケース選択/解除
  const toggleTestCase = (id: string) => {
    if (selectedTestCases.includes(id)) {
      setSelectedTestCases(selectedTestCases.filter(tcId => tcId !== id));
    } else {
      setSelectedTestCases([...selectedTestCases, id]);
    }
  };
  
  // テスト実行
  const handleRunTests = async () => {
    if (selectedTestCases.length === 0) {
      toast.error('テストケースが選択されていません');
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
          test_case_ids: selectedTestCases,
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
        <h1 className="text-3xl font-bold">テスト実行</h1>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>テストケース選択</CardTitle>
          <CardDescription>
            実行するテストケースを選択してください。
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
              disabled={isRunning || selectedTestCases.length === 0}
            >
              <PlayIcon className="h-4 w-4 mr-2" />
              {isRunning ? 'テスト実行中...' : 'テスト実行'}
            </Button>
          </div>
          
          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="relative flex-1">
              <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="テストケースを検索..."
                className="pl-8"
                value={searchQuery}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="select-all"
                checked={filteredTestCases.length > 0 && selectedTestCases.length === filteredTestCases.length}
                onCheckedChange={toggleSelectAll}
              />
              <label htmlFor="select-all" className="text-sm">すべて選択</label>
            </div>
          </div>
          
          {isLoading ? (
            <div className="text-center py-8">読み込み中...</div>
          ) : filteredTestCases.length > 0 ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]"></TableHead>
                    <TableHead className="w-[300px]">タイトル</TableHead>
                    <TableHead className="w-[80px]">メソッド</TableHead>
                    <TableHead>パス</TableHead>
                    <TableHead className="w-[120px]">期待するステータス</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTestCases.map((testCase) => (
                    <TestCaseRow
                      key={testCase.id}
                      testCase={testCase}
                      isSelected={selectedTestCases.includes(testCase.id)}
                      onToggle={() => toggleTestCase(testCase.id)}
                    />
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8 border rounded-lg bg-background">
              <p className="text-muted-foreground">テストケースが見つかりません</p>
              {searchQuery ? (
                <p className="mt-2">検索条件を変更してください</p>
              ) : (
                <div className="mt-4">
                  <p className="mb-2">テストケースを生成してください</p>
                  <Button asChild>
                    <Link href={`/projects/${projectId}/generate`}>
                      テスト生成
                    </Link>
                  </Button>
                </div>
              )}
            </div>
          )}
          
          {filteredTestCases.length > 0 && (
            <div className="flex justify-end">
              <Button
                onClick={handleRunTests}
                disabled={isRunning || selectedTestCases.length === 0}
              >
                <PlayIcon className="h-4 w-4 mr-2" />
                {isRunning ? 'テスト実行中...' : `選択したテストを実行 (${selectedTestCases.length}件)`}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}