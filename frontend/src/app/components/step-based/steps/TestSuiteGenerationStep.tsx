"use client"

import React, { useState } from 'react';
import { useUIMode } from '@/contexts/UIModeContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Loader2, Sparkles, AlertCircle, Check } from 'lucide-react';
import { fetcher } from '@/utils/fetcher';

export function TestSuiteGenerationStep() {
  const { sharedData, updateSharedData } = useUIMode();
  const serviceId = sharedData.serviceId;
  const selectedEndpoints = sharedData.selectedEndpoints || [];
  
  const [suiteName, setSuiteName] = useState(sharedData.testSuiteName || '');
  const [description, setDescription] = useState(sharedData.testSuiteDescription || '');
  const [additionalInstructions, setAdditionalInstructions] = useState(sharedData.additionalInstructions || '');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [isGenerated, setIsGenerated] = useState(false);
  
  const handleGenerateTests = async () => {
    if (!serviceId) {
      toast.error("サービスIDがありません", {
        description: "先にサービスを作成してください",
      });
      return;
    }
    
    if (selectedEndpoints.length === 0) {
      toast.error("エンドポイントが選択されていません", {
        description: "先にテスト対象のエンドポイントを選択してください",
      });
      return;
    }
    
    if (!suiteName) {
      toast.error("テストスイート名が入力されていません", {
        description: "テストスイート名を入力してください",
      });
      return;
    }
    
    setIsGenerating(true);
    setGenerationProgress(0);
    
    try {
      toast.info("テスト生成を開始しました", {
        description: "AIによるテストケース生成を開始しました。完了までしばらくお待ちください。",
      });
      
      const progressInterval = setInterval(() => {
        setGenerationProgress(prev => {
          const newProgress = prev + Math.random() * 10;
          return newProgress >= 100 ? 100 : newProgress;
        });
      }, 1000);
      
      const response = await fetcher(`/api/services/${serviceId}/generate-tests`, 'POST', {
        name: suiteName,
        description: description,
        endpoint_ids: selectedEndpoints,
        additional_instructions: additionalInstructions || undefined,
      });
      
      clearInterval(progressInterval);
      setGenerationProgress(100);
      
      updateSharedData('testSuiteId', response.id);
      updateSharedData('testSuiteName', suiteName);
      updateSharedData('testSuiteDescription', description);
      updateSharedData('additionalInstructions', additionalInstructions);
      updateSharedData('generatedTestCases', response.test_cases || []);
      
      setIsGenerated(true);
      toast.success("テストスイートを生成しました", {
        description: `${response.test_cases?.length || 0}個のテストケースが生成されました`,
      });
      
    } catch (error) {
      console.error('テスト生成エラー:', error);
      toast.error("テスト生成エラー", {
        description: "テストスイートの生成中にエラーが発生しました",
      });
    } finally {
      setIsGenerating(false);
    }
  };
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>テストスイートの生成</CardTitle>
        <CardDescription>
          選択したエンドポイントに対するテストケースを自動生成します
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* テストスイート情報入力 */}
        <div className="space-y-2">
          <Label htmlFor="suite-name">テストスイート名 *</Label>
          <Input
            id="suite-name"
            placeholder="例: ユーザーAPI基本テスト"
            value={suiteName}
            onChange={(e) => setSuiteName(e.target.value)}
            disabled={isGenerating || isGenerated}
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="suite-description">説明</Label>
          <Textarea
            id="suite-description"
            placeholder="テストスイートの目的や範囲を入力してください"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            disabled={isGenerating || isGenerated}
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="additional-instructions">追加指示（オプション）</Label>
          <Textarea
            id="additional-instructions"
            placeholder="AIに対する特別な指示があれば入力してください（例: 特定のエッジケースをテストする、認証に関するテストを重視するなど）"
            value={additionalInstructions}
            onChange={(e) => setAdditionalInstructions(e.target.value)}
            rows={3}
            disabled={isGenerating || isGenerated}
          />
        </div>
        
        {/* 選択エンドポイント情報 */}
        <div className="rounded-md bg-muted p-3">
          <div className="flex justify-between items-center mb-2">
            <h4 className="text-sm font-medium">選択済みエンドポイント</h4>
            <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
              {selectedEndpoints.length}個
            </span>
          </div>
          
          {selectedEndpoints.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              エンドポイントが選択されていません。前のステップに戻って選択してください。
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              選択したエンドポイントに対してテストケースを生成します。
            </p>
          )}
        </div>
        
        {/* 生成中プログレス */}
        {isGenerating && (
          <div className="space-y-2 py-2">
            <div className="flex justify-between text-xs">
              <span>生成中...</span>
              <span>{Math.round(generationProgress)}%</span>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div 
                className="bg-primary h-2 rounded-full transition-all duration-300"
                style={{ width: `${generationProgress}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground text-center animate-pulse">
              AIがテストケースを生成しています。しばらくお待ちください...
            </p>
          </div>
        )}
        
        {/* 注意事項 */}
        <div className="flex items-start gap-2 text-sm text-muted-foreground">
          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <p>
            生成されたテストケースは自動的に保存され、次のステップで実行できます。
            また、後からテストスイート管理画面で編集することも可能です。
          </p>
        </div>
        
        {/* 生成ボタン */}
        <Button 
          className="w-full" 
          onClick={handleGenerateTests}
          disabled={isGenerating || isGenerated || selectedEndpoints.length === 0 || !suiteName}
        >
          {isGenerating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              テスト生成中...
            </>
          ) : isGenerated ? (
            <>
              <Check className="mr-2 h-4 w-4" />
              テスト生成済み
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              AIでテストを生成
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
