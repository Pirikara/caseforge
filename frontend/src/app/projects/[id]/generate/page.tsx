"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useProjects } from '../../../hooks/useProjects';
import { Button } from '../../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../components/ui/card';
import { ArrowLeftIcon, FileTextIcon, PlayIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from 'lucide-react';
import { toast } from 'sonner';

// メモ化されたステータスアイコンコンポーネント
const StatusIcon = React.memo(({ status }: { status: string }) => {
  if (status === 'completed') {
    return <CheckCircleIcon className="h-12 w-12 text-green-500" />;
  } else if (status === 'failed') {
    return <XCircleIcon className="h-12 w-12 text-red-500" />;
  } else if (status === 'generating') {
    return <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>;
  } else {
    return <FileTextIcon className="h-12 w-12 text-primary" />;
  }
});

export default function GenerateTestsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  
  const { projects, isLoading: isLoadingProjects } = useProjects();
  const project = React.useMemo(() => {
    if (!projects) return null;
    return projects.find(p => p.id === projectId);
  }, [projects, projectId]);
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [generationStatus, setGenerationStatus] = React.useState<'idle' | 'generating' | 'completed' | 'failed'>('idle');
  const [generatedCount, setGeneratedCount] = React.useState(0);
  
  // エラーメッセージ状態
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
        <h1 className="text-3xl font-bold">テスト生成</h1>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>AIテスト生成</CardTitle>
          <CardDescription>
            OpenAPIスキーマに基づいてAIがテストケースを自動生成します。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 p-4 bg-muted rounded-lg">
            <div className="flex-shrink-0">
              <FileTextIcon className="h-10 w-10 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold">{project.name}</h3>
              <p className="text-sm text-muted-foreground">
                {project.description || 'プロジェクトの説明はありません'}
              </p>
            </div>
          </div>
          
          <div className="border rounded-lg p-4">
            <h3 className="font-semibold mb-2">テスト生成について</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start gap-2">
                <CheckCircleIcon className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>OpenAPIスキーマの各エンドポイントに対してテストケースを生成します</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircleIcon className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>正常系・異常系の両方のテストケースを生成します</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircleIcon className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>生成されたテストケースはプロジェクトに保存され、いつでも実行できます</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircleIcon className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>テスト生成には数分かかる場合があります</span>
              </li>
            </ul>
          </div>
          
          {generationStatus === 'idle' && (
            <div className="flex justify-center">
              <Button 
                size="lg" 
                onClick={handleGenerateTests} 
                disabled={isGenerating}
              >
                <FileTextIcon className="h-5 w-5 mr-2" />
                テスト生成を開始
              </Button>
            </div>
          )}
          
          {generationStatus === 'generating' && (
            <div className="text-center p-6 space-y-4">
              <div className="flex justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
              </div>
              <p className="font-medium">テスト生成中...</p>
              <p className="text-sm text-muted-foreground">
                OpenAPIスキーマを解析してテストケースを生成しています。
                <br />
                この処理には数分かかる場合があります。
              </p>
            </div>
          )}
          
          {generationStatus === 'completed' && (
            <div className="text-center p-6 space-y-4 bg-green-50 dark:bg-green-950 rounded-lg">
              <div className="flex justify-center">
                <StatusIcon status="completed" />
              </div>
              <p className="font-medium">テスト生成が完了しました</p>
              <p className="text-sm">
                {generatedCount}件のテストケースが生成されました。
              </p>
              <div className="flex justify-center gap-2">
                <Button asChild variant="outline">
                  <Link href={`/projects/${projectId}/tests`}>
                    <FileTextIcon className="h-4 w-4 mr-2" />
                    テストケース一覧を表示
                  </Link>
                </Button>
                <Button asChild>
                  <Link href={`/projects/${projectId}/run`}>
                    <PlayIcon className="h-4 w-4 mr-2" />
                    テストを実行
                  </Link>
                </Button>
              </div>
            </div>
          )}
          
          {generationStatus === 'failed' && (
            <div className="text-center p-6 space-y-4 bg-red-50 dark:bg-red-950 rounded-lg">
              <div className="flex justify-center">
                <StatusIcon status="failed" />
              </div>
              <p className="font-medium">テスト生成に失敗しました</p>
              <p className="text-sm text-muted-foreground">
                エラーが発生したため、テスト生成を完了できませんでした。
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
                <Button variant="outline" asChild>
                  <Link href={`/projects/${projectId}/schema`}>
                    スキーマを確認/更新
                  </Link>
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}