"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useProjects } from '@/hooks/useProjects';
import { useTestCases } from '@/hooks/useTestCases';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeftIcon, PlayIcon } from 'lucide-react';

export default function TestCaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const caseId = params.case_id as string;
  
  const { projects } = useProjects();
  const { testCases, isLoading } = useTestCases(projectId);
  
  const project = React.useMemo(() => {
    if (!projects) return null;
    return projects.find(p => p.id === projectId);
  }, [projects, projectId]);
  
  const testCase = React.useMemo(() => {
    if (!testCases) return null;
    return testCases.find(tc => tc.case_id === caseId);
  }, [testCases, caseId]);
  
  if (isLoading) {
    return <div className="text-center py-8">読み込み中...</div>;
  }
  
  if (!project || !testCase) {
    return (
      <div className="text-center py-8">
        <p>テストケースが見つかりません</p>
        <Button asChild className="mt-4">
          <Link href={`/projects/${projectId}/tests`}>テストケース一覧に戻る</Link>
        </Button>
      </div>
    );
  }
  
  // JSONを整形して表示
  const formatJSON = (json: any) => {
    try {
      return JSON.stringify(json, null, 2);
    } catch (e) {
      return String(json);
    }
  };
  
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/projects/${projectId}/tests`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            テストケース一覧に戻る
          </Link>
        </Button>
      </div>
      
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">{testCase.title}</h1>
        <Button asChild>
          <Link href={`/projects/${projectId}/run?case_id=${caseId}`}>
            <PlayIcon className="h-4 w-4 mr-2" />
            このテストを実行
          </Link>
        </Button>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>テストケース情報</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4">
              <div className="flex justify-between">
                <dt className="font-medium">テストケースID</dt>
                <dd className="text-muted-foreground">{testCase.case_id}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">HTTPメソッド</dt>
                <dd>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    testCase.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200' :
                    testCase.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200' :
                    testCase.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200' :
                    testCase.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200' :
                    'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200'
                  }`}>
                    {testCase.method}
                  </span>
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">パス</dt>
                <dd className="text-muted-foreground font-mono">{testCase.path}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">期待するステータスコード</dt>
                <dd className="text-muted-foreground">{testCase.expected_status}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>テストの目的</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap">{testCase.purpose}</p>
          </CardContent>
        </Card>
      </div>
      
      <Tabs defaultValue="request">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="request">リクエスト</TabsTrigger>
          <TabsTrigger value="response">期待するレスポンス</TabsTrigger>
        </TabsList>
        <TabsContent value="request" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>リクエスト詳細</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-muted p-4 rounded-md overflow-auto">
                <pre className="font-mono text-sm">
                  {testCase.request_body ? formatJSON(testCase.request_body) : 'リクエストボディなし'}
                </pre>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="response" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>期待するレスポンス</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-muted p-4 rounded-md overflow-auto">
                <pre className="font-mono text-sm">
                  {testCase.expected_response ? formatJSON(testCase.expected_response) : '期待するレスポンスの詳細なし'}
                </pre>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}