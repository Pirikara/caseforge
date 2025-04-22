"use client"

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileUpload } from '@/components/molecules/FileUpload';
import { toast } from 'sonner';

export default function SchemaUploadPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const [isUploading, setIsUploading] = React.useState(false);

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
        <h1 className="text-3xl font-bold">スキーマのアップロード</h1>
        <Button variant="outline" asChild>
          <Link href={`/projects/${projectId}`}>
            戻る
          </Link>
        </Button>
      </div>
      
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
    </div>
  );
}