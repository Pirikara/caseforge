"use client"

import React, { useState } from 'react';
import { useUIMode } from '@/contexts/UIModeContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { fetcher } from '@/utils/fetcher';

export function ServiceCreateStep() {
  const { updateSharedData, sharedData } = useUIMode();
  
  const [name, setName] = useState(sharedData.serviceName || '');
  const [description, setDescription] = useState(sharedData.serviceDescription || '');
  const [baseUrl, setBaseUrl] = useState(sharedData.serviceBaseUrl || '');
  const [isLoading, setIsLoading] = useState(false);
  
  const handleCreateService = async () => {
    if (!name) {
      toast.error("エラー", {
        description: "サービス名を入力してください",
      });
      return;
    }
    
    setIsLoading(true);
    
    try {
      const response = await fetcher('/api/services/', 'POST', {
        name,
        description,
        base_url: baseUrl,
      });
      
      updateSharedData('serviceId', response.id);
      updateSharedData('serviceName', name);
      updateSharedData('serviceDescription', description);
      updateSharedData('serviceBaseUrl', baseUrl);
      
      toast.success("サービスを作成しました", {
        description: `${name} サービスが正常に作成されました`,
      });
      
    } catch (error) {
      console.error('サービス作成エラー:', error);
      toast.error("サービス作成エラー", {
        description: "サービスの作成中にエラーが発生しました",
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>サービス作成</CardTitle>
        <CardDescription>
          テスト対象のAPIサービスの基本情報を入力してください
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="service-name">サービス名 *</Label>
          <Input
            id="service-name"
            placeholder="例: ユーザー管理API"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="service-description">説明</Label>
          <Textarea
            id="service-description"
            placeholder="サービスの説明を入力してください"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="base-url">ベースURL</Label>
          <Input
            id="base-url"
            placeholder="例: https://api.example.com"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            テスト実行時に使用するAPIのベースURLです
          </p>
        </div>
        
        <Button 
          className="w-full mt-4" 
          onClick={handleCreateService}
          disabled={isLoading}
        >
          {isLoading ? "作成中..." : "サービスを作成"}
        </Button>
      </CardContent>
    </Card>
  );
}
