"use client"

import * as React from 'react';
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
import { FileTextIcon, CheckCircleIcon, XCircleIcon } from 'lucide-react';
import { useTestChains } from '@/hooks/useTestChains';
import { toast } from 'sonner';

export const TestChainManagementTab = ({ projectId, project }: { projectId: string, project: any }) => {
  const { testChains, isLoading: isLoadingTestChains } = useTestChains(projectId);
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [generationStatus, setGenerationStatus] = React.useState<'idle' | 'generating' | 'completed' | 'failed'>('idle');
  const [generatedCount, setGeneratedCount] = React.useState(0);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  // テスト生成を開始
  const handleGenerateTests = async () => {
    try {
      setIsGenerating(true);
      setGenerationStatus('generating');
      setErrorMessage(null);
      
      console.log(`Sending test generation request for project: ${projectId}`);
      const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
      const url = `${API}/api/projects/${projectId}/generate-tests`;
      console.log(`API URL: ${url}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      console.log(`Response status: ${response.status}`);
      const responseText = await response.text();
      console.log(`Response text: ${responseText}`);
      
      let data;
      try {
        data = JSON.parse(responseText);
      } catch (e) {
        console.error('Failed to parse response as JSON:', e);
        throw new Error(`Invalid response format: ${responseText}`);
      }
      
      if (!response.ok) {
        const errorMsg = data?.detail || 'テスト生成に失敗しました';
        console.error('API error:', errorMsg);
        setErrorMessage(errorMsg);
        throw new Error(errorMsg);
      }
      
      if (data.status === 'error') {
        const errorMsg = data.message || 'テスト生成に失敗しました';
        console.error('Task error:', errorMsg);
        setErrorMessage(errorMsg);
        throw new Error(errorMsg);
      }
      
      console.log('Test generation task started successfully:', data);
      
      // 非同期タスクの場合は、ここでは完了とみなさない
      // 実際のアプリケーションでは、WebSocketやポーリングで状態を確認する必要がある
      // ここではデモのために、タスクが開始されたら成功とみなす
      setGenerationStatus('completed');
      setGeneratedCount(data.count || 0);
      
      toast.success('テスト生成タスクが開始されました', {
        description: 'バックグラウンドでテスト生成が実行されています。しばらくしてからテストケース一覧を確認してください。',
      });
    } catch (error) {
      console.error('テスト生成エラー:', error);
      setGenerationStatus('failed');
      
      toast.error('エラーが発生しました', {
        description: error instanceof Error ? error.message : '不明なエラーが発生しました',
      });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>テストチェーン一覧</CardTitle>
          <CardDescription>
            生成されたテストチェーンの一覧です。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex justify-end mb-4">
            <Button onClick={handleGenerateTests} disabled={isGenerating}>
              <FileTextIcon className="h-4 w-4 mr-2" />
              {isGenerating ? 'テスト生成中...' : 'テストチェーン生成'}
            </Button>
          </div>

          {generationStatus === 'generating' && (
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
          )}

          {generationStatus === 'completed' && (
            <div className="text-center p-6 space-y-4 mb-4 bg-green-50 dark:bg-green-950 rounded-lg">
              <div className="flex justify-center">
                <CheckCircleIcon className="h-12 w-12 text-green-500" />
              </div>
              <p className="font-medium">テストチェーン生成が完了しました</p>
              <p className="text-sm">
                {generatedCount}件のテストチェーンが生成されました。
              </p>
            </div>
          )}

          {generationStatus === 'failed' && (
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
          )}
          
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
                  {testChains.map((chain) => (
                    <TableRow key={chain.id}>
                      <TableCell className="font-medium">{chain.name}</TableCell>
                      <TableCell>{chain.steps_count}</TableCell>
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
                      <TableCell>
                        <Button variant="outline" size="sm" onClick={() => {
                          // テスト実行タブに遷移し、このチェーンを選択状態にする
                          document.querySelector('[data-value="test-execution"]')?.dispatchEvent(
                            new MouseEvent('click', { bubbles: true })
                          );
                        }}>
                          実行
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
        </CardContent>
      </Card>
    </div>
  );
};

export default TestChainManagementTab;