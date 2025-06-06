"use client"

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useServices } from '@/hooks/useServices';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { updateService } from '@/utils/fetcher';
import { toast } from 'sonner';

interface ServiceDetailLayoutProps {
  children?: React.ReactNode;
  activeTab: string;
  onTabChange: (value: string) => void;
}

export function ServiceDetailLayout({ 
  children, 
  activeTab, 
  onTabChange 
}: ServiceDetailLayoutProps) {
  const params = useParams();
  const router = useRouter();
  const serviceId = parseInt(params.id as string, 10);

  const { services, isLoading, error, mutate } = useServices();

  const service = React.useMemo(() => {
    if (!services) return null;
    return services.find(p => p.id === serviceId);
  }, [services, serviceId]);

  const [baseUrl, setBaseUrl] = React.useState<string>('');

  React.useEffect(() => {
    if (service) {
      setBaseUrl(service.base_url || '');
    }
  }, [service]);

  const handleSaveBaseUrl = async () => {
    try {
      await updateService(serviceId, { base_url: baseUrl });
      mutate();
      toast.success("Base URLを保存しました");
    } catch (error) {
      toast.error("Base URLの保存に失敗しました");
    }
  };

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <p>読み込み中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p>サービスの読み込みに失敗しました。</p>
        <p className="text-muted-foreground">{error.message}</p>
      </div>
    );
  }

  if (!service) {
    return (
      <div className="text-center py-8">
        <p>サービスが見つかりません</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">{service.name}</h1>
      </div>

      {service.description && (
        <p className="text-muted-foreground">{service.description}</p>
      )}

      <div className="flex items-end space-x-2">
        <div className="flex-grow space-y-2">
          <Label htmlFor="baseUrl">Base URL</Label>
          <Input
            id="baseUrl"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="例: http://localhost:8000"
          />
        </div>
        <Button onClick={handleSaveBaseUrl}>保存</Button>
      </div>

      <Tabs value={activeTab} onValueChange={onTabChange} className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="schema">スキーマ管理</TabsTrigger>
          <TabsTrigger value="endpoints">エンドポイント管理</TabsTrigger>
          <TabsTrigger value="test-suites">テストスイート管理・実行</TabsTrigger>
        </TabsList>

        {children}
      </Tabs>
    </div>
  );
}
