"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useProjects } from '@/hooks/useProjects';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import SchemaManagementTab from '@/components/tabs/SchemaManagementTab';
import EndpointManagementTab from '@/components/tabs/EndpointManagementTab';
import TestChainManagementTab from '@/components/tabs/TestChainManagementTab';
import TestExecutionTab from '@/components/tabs/TestExecutionTab';

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  
  const { projects } = useProjects();
  
  const project = React.useMemo(() => {
    if (!projects) return null;
    return projects.find(p => p.id === projectId);
  }, [projects, projectId]);
  
  // URLからタブを取得（例：?tab=test-chains）
  const [activeTab, setActiveTab] = React.useState<string>('schema');
  
  React.useEffect(() => {
    // URLからタブパラメータを取得
    const url = new URL(window.location.href);
    const tabParam = url.searchParams.get('tab');
    if (tabParam && ['schema', 'endpoints', 'test-chains', 'test-execution'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
  }, []);
  
  // タブ変更時にURLを更新
  const handleTabChange = (value: string) => {
    setActiveTab(value);
    
    // URLのクエリパラメータを更新（履歴に残さない）
    const url = new URL(window.location.href);
    url.searchParams.set('tab', value);
    window.history.replaceState({}, '', url.toString());
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
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">{project.name}</h1>
        <Button asChild variant="outline">
          <Link href="/projects">
            プロジェクト一覧に戻る
          </Link>
        </Button>
      </div>
      
      {project.description && (
        <p className="text-muted-foreground">{project.description}</p>
      )}
      
      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="schema">スキーマ管理</TabsTrigger>
          <TabsTrigger value="endpoints">エンドポイント管理</TabsTrigger>
          <TabsTrigger value="test-chains">テストチェーン管理</TabsTrigger>
          <TabsTrigger value="test-execution">テスト実行</TabsTrigger>
        </TabsList>
        
        <TabsContent value="schema" className="space-y-4">
          <SchemaManagementTab projectId={projectId} />
        </TabsContent>
        
        <TabsContent value="endpoints" className="space-y-4">
          <EndpointManagementTab projectId={projectId} />
        </TabsContent>
        
        <TabsContent value="test-chains" className="space-y-4">
          <TestChainManagementTab projectId={projectId} project={project} />
        </TabsContent>
        
        <TabsContent value="test-execution" className="space-y-4">
          <TestExecutionTab projectId={projectId} project={project} />
        </TabsContent>
      </Tabs>
    </div>
  );
}