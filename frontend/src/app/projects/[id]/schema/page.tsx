"use client"

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileUpload } from '@/components/molecules/FileUpload';
import { toast } from 'sonner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function SchemaPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const [isUploading, setIsUploading] = React.useState(false);
  const [schema, setSchema] = React.useState<{ filename: string; content: string; content_type: string } | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // スキーマを取得する関数
  const fetchSchema = React.useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
      const response = await fetch(`${API}/api/projects/${projectId}/schema`);
      
      if (!response.ok) {
        if (response.status === 404) {
          // スキーマが見つからない場合は、エラーメッセージを表示せずに終了
          setIsLoading(false);
          return;
        }
        const errorData = await response.json();
        throw new Error(errorData.detail || 'スキーマの取得に失敗しました');
      }
      
      const data = await response.json();
      setSchema(data);
    } catch (error) {
      console.error('スキーマ取得エラー:', error);
      setError(error instanceof Error ? error.message : '不明なエラーが発生しました');
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  // コンポーネントのマウント時にスキーマを取得
  React.useEffect(() => {
    fetchSchema();
  }, [fetchSchema]);

  const handleUpload = async (file: File) => {
    if (!file) return;

    // YAMLまたはJSONファイルのみ許可
    const validTypes = ['application/json', 'application/x-yaml', 'text/yaml', 'text/x-yaml'];
    if (!validTypes.includes(file.type) && !file.name.endsWith('.yaml') && !file.name.endsWith('.yml') && !file.name.endsWith('.json')) {
      toast.error('無効なファイル形式です', {
        description: 'YAMLまたはJSONファイルのみアップロードできます。',
      });
      return;
    }

    try {
      setIsUploading(true);
      
      const formData = new FormData();
      formData.append('file', file);
      
      const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
      const response = await fetch(`${API}/api/projects/${projectId}/schema`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'スキーマのアップロードに失敗しました');
      }
      
      toast.success('スキーマがアップロードされました', {
        description: 'スキーマが正常にアップロードされました。',
      });
      
      // プロジェクト詳細ページにリダイレクト
      router.push(`/projects/${projectId}`);
    } catch (error) {
      console.error('スキーマアップロードエラー:', error);
      toast.error('エラーが発生しました', {
        description: error instanceof Error ? error.message : '不明なエラーが発生しました',
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">スキーマ管理</h1>
        <Button variant="outline" asChild>
          <Link href={`/projects/${projectId}`}>
            戻る
          </Link>
        </Button>
      </div>
      
      <Tabs defaultValue="view">
        <TabsList className="mb-4">
          <TabsTrigger value="view">スキーマ表示</TabsTrigger>
          <TabsTrigger value="upload">スキーマアップロード</TabsTrigger>
        </TabsList>
        
        <TabsContent value="view">
          <Card>
            <CardHeader>
              <CardTitle>OpenAPIスキーマ</CardTitle>
              <CardDescription>
                プロジェクトのOpenAPIスキーマ情報
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="py-8 text-center">読み込み中...</div>
              ) : error ? (
                <div className="py-8 text-center text-red-500">{error}</div>
              ) : !schema ? (
                <div className="py-8 text-center">
                  <p className="mb-4">スキーマがまだアップロードされていません。</p>
                  <Button onClick={() => {
                    const element = document.querySelector('[data-value="upload"]');
                    if (element instanceof HTMLElement) {
                      element.click();
                    }
                  }}>
                    スキーマをアップロード
                  </Button>
                </div>
              ) : (
                <div>
                  <div className="mb-4">
                    <p><strong>ファイル名:</strong> {schema.filename}</p>
                    <p><strong>形式:</strong> {schema.content_type === 'application/json' ? 'JSON' : 'YAML'}</p>
                  </div>
                  <div className="border rounded-md p-4 bg-gray-50 dark:bg-gray-900 overflow-auto max-h-96">
                    <pre className="text-xs">{schema.content}</pre>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="upload">
          <Card>
            <CardHeader>
              <CardTitle>OpenAPIスキーマのアップロード</CardTitle>
              <CardDescription>
                YAMLまたはJSONフォーマットのOpenAPIスキーマファイルをアップロードしてください。
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className={isUploading ? "opacity-50 pointer-events-none" : ""}>
                <FileUpload
                  onFileSelect={handleUpload}
                  accept=".yaml,.yml,.json"
                  maxSize={5} // 5MB
                />
              </div>
              
              <div className="mt-6 text-sm text-muted-foreground">
                <p>サポートされているファイル形式: YAML (.yaml, .yml), JSON (.json)</p>
                <p>最大ファイルサイズ: 5MB</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}