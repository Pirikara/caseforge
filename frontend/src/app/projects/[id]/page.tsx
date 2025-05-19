"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useServices } from '@/hooks/useServices';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import SchemaManagementTab from '@/components/tabs/SchemaManagementTab';
import EndpointManagementTab from '@/components/tabs/EndpointManagementTab';
import TestSuiteManagementTab from '@/components/tabs/TestSuiteManagementTab';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { updateService } from '@/utils/fetcher';
// import TestExecutionTab from '@/components/tabs/TestExecutionTab'; // TestExecutionTabは削除

export default function ServiceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;

  const { services, isLoading, error, mutate } = useServices();

  const service = React.useMemo(() => {
    if (!services) return null;
    return services.find(p => p.id === serviceId);
  }, [services, serviceId]);

  // URLからタブを取得（例：?tab=test-chains）
  const [activeTab, setActiveTab] = React.useState<string>('schema');
  const [baseUrl, setBaseUrl] = React.useState<string>('');

  React.useEffect(() => {
    // URLからタブパラメータを取得
    const url = new URL(window.location.href);
    const tabParam = url.searchParams.get('tab');
    // test-executionタブを削除したので、有効なタブリストから除外
    if (tabParam && ['schema', 'endpoints', 'test-suites'].includes(tabParam)) {
      setActiveTab(tabParam);
    } else {
      // 無効なタブパラメータの場合はデフォルトに戻す
      setActiveTab('schema');
    }
  }, []);

  React.useEffect(() => {
    if (service) {
      console.log('Service data updated:', service); // 追加
      console.log('Base URL from service:', service.base_url); // 追加
      setBaseUrl(service.base_url || '');
    }
  }, [service]);

  // タブ変更時にURLを更新
  const handleTabChange = (value: string) => {
    setActiveTab(value);

    // URLのクエリパラメータを更新（履歴に残さない）
    const url = new URL(window.location.href);
    url.searchParams.set('tab', value);
    window.history.replaceState({}, '', url.toString());
  };

  const handleSaveBaseUrl = async () => {
    try {
      await updateService(serviceId, { base_url: baseUrl });
      mutate(); // サービスデータを再取得
      console.log('Base URL saved successfully!'); // 仮の成功メッセージ
    } catch (error) {
      console.error('Failed to save Base URL:', error); // 仮のエラーメッセージ
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
        <Button asChild className="mt-4">
          <Link href="/services">サービス一覧に戻る</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">{service.name}</h1>
        <Button asChild variant="outline">
          <Link href="/services">
            サービス一覧に戻る
          </Link>
        </Button>
      </div>

      {service.description && (
        <p className="text-muted-foreground">{service.description}</p>
      )}

      {/* Base URL Setting */}
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

      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-4">
        {/* grid-cols-4 を grid-cols-3 に変更し、test-execution タブを削除 */}
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="schema">スキーマ管理</TabsTrigger>
          <TabsTrigger value="endpoints">エンドポイント管理</TabsTrigger>
          <TabsTrigger value="test-suites">テストスイート管理・実行</TabsTrigger>
        </TabsList>

        <TabsContent value="schema" className="space-y-4">
          <SchemaManagementTab serviceId={serviceId} />
        </TabsContent>

        <TabsContent value="endpoints" className="space-y-4">
          <EndpointManagementTab serviceId={serviceId} />
        </TabsContent>

        <TabsContent value="test-suites" className="space-y-4">
          <TestSuiteManagementTab serviceId={serviceId} service={service} />
        </TabsContent>

        {/* test-execution タブのコンテンツを削除 */}
        {/* <TabsContent value="test-execution" className="space-y-4">
          <TestExecutionTab serviceId={serviceId} service={service} />
        </TabsContent> */}
      </Tabs>
    </div>
  );
}
