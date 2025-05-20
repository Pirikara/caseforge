"use client"

import React, { useState } from 'react';
import { useUIMode } from '@/contexts/UIModeContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { Upload, FileText, Check, AlertCircle } from 'lucide-react';
import { fetcher } from '@/utils/fetcher';

export function SchemaUploadStep() {
  const { sharedData, updateSharedData } = useUIMode();
  const serviceId = sharedData.serviceId;
  
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isUploaded, setIsUploaded] = useState(false);
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (
        selectedFile.type === 'application/json' || 
        selectedFile.name.endsWith('.json') ||
        selectedFile.name.endsWith('.yaml') ||
        selectedFile.name.endsWith('.yml')
      ) {
        setFile(selectedFile);
        setIsUploaded(false);
      } else {
        toast.error("不正なファイル形式", {
          description: "JSONまたはYAMLファイルを選択してください",
        });
      }
    }
  };
  
  // スキーマアップロード処理
  const handleUploadSchema = async () => {
    if (!serviceId) {
      toast.error("サービスIDがありません", {
        description: "先にサービスを作成してください",
      });
      return;
    }
    
    if (!file) {
      toast.error("ファイルが選択されていません", {
        description: "OpenAPIスキーマファイルを選択してください",
      });
      return;
    }
    
    setIsUploading(true);
    
    try {
      // FormDataの作成
      const formData = new FormData();
      formData.append('file', file);
      
      // APIリクエスト
      const response = await fetch(`/api/services/${serviceId}/schema`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`アップロード失敗: ${response.status}`);
      }
      
      const data = await response.json();
      
      // スキーマ情報を共有データに保存
      updateSharedData('schemaId', data.id);
      updateSharedData('schemaVersion', data.version);
      
      setIsUploaded(true);
      toast.success("スキーマをアップロードしました", {
        description: `${file.name} が正常にアップロードされました`,
      });
      
    } catch (error) {
      console.error('スキーマアップロードエラー:', error);
      toast.error("スキーマアップロードエラー", {
        description: "スキーマのアップロード中にエラーが発生しました",
      });
    } finally {
      setIsUploading(false);
    }
  };
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>OpenAPIスキーマのアップロード</CardTitle>
        <CardDescription>
          テスト対象のAPIのOpenAPIスキーマ（JSON/YAML）をアップロードしてください
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* ファイル選択エリア */}
        <div className="flex flex-col items-center justify-center border-2 border-dashed border-muted-foreground/25 rounded-lg p-12 text-center">
          <input
            type="file"
            id="schema-file"
            className="hidden"
            accept=".json,.yaml,.yml"
            onChange={handleFileChange}
          />
          
          {file ? (
            <div className="flex flex-col items-center gap-2">
              <FileText className="h-10 w-10 text-muted-foreground" />
              <p className="font-medium">{file.name}</p>
              <p className="text-xs text-muted-foreground">
                {(file.size / 1024).toFixed(2)} KB
              </p>
              {isUploaded ? (
                <div className="flex items-center gap-2 text-green-500 mt-2">
                  <Check className="h-4 w-4" />
                  <span>アップロード済み</span>
                </div>
              ) : (
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="mt-2"
                  onClick={() => document.getElementById('schema-file')?.click()}
                >
                  ファイルを変更
                </Button>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="h-10 w-10 text-muted-foreground" />
              <p className="text-muted-foreground">
                ファイルをドラッグ＆ドロップするか、クリックして選択してください
              </p>
              <Button 
                variant="outline" 
                onClick={() => document.getElementById('schema-file')?.click()}
              >
                ファイルを選択
              </Button>
            </div>
          )}
        </div>
        
        {/* 注意事項 */}
        <div className="flex items-start gap-2 text-sm text-muted-foreground">
          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <p>
            OpenAPI 3.0または3.1形式のJSONまたはYAMLファイルをアップロードしてください。
            スキーマはAPIのエンドポイント、パラメータ、レスポンスの定義を含む必要があります。
          </p>
        </div>
        
        {/* アップロードボタン */}
        <Button 
          className="w-full" 
          onClick={handleUploadSchema}
          disabled={!file || isUploading || isUploaded}
        >
          {isUploading ? "アップロード中..." : isUploaded ? "アップロード済み" : "スキーマをアップロード"}
        </Button>
      </CardContent>
    </Card>
  );
}
