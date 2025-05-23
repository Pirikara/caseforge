"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useServices, Service } from '@/hooks/useProjects';
import { useTestRuns, useTestRunDetail } from '@/hooks/useTestRuns';
import { TestCaseResult, StepResult, TestCase } from '@/hooks/useTestRuns';
import { useTestCases } from '@/hooks/useTestCases';
import { useTestSuiteDetail } from '@/hooks/useTestChains';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeftIcon, 
  CheckCircleIcon, 
  XCircleIcon, 
  ClockIcon,
  BarChart3Icon,
  ListIcon,
  PieChartIcon
} from 'lucide-react';
import { format } from 'date-fns';
import dynamic from 'next/dynamic';

const TestRunSummary = dynamic(
  () => import('@/components/molecules/TestRunSummary'),
  {
    ssr: false,
    loading: () => (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }
);

const TestCaseResultList = dynamic(
  () => import('@/components/molecules/TestCaseResultList'),
  {
    ssr: false,
    loading: () => (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }
);

const TestStepResultList = dynamic(
  () => import('@/components/molecules/TestStepResultList'),
  {
    ssr: false,
    loading: () => (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }
);

const SuccessRateChart = dynamic(
  () => import('@/components/molecules/SuccessRateChart'),
  {
    ssr: false,
    loading: () => (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }
);

const ResponseTimeChart = dynamic(
  () => import('@/components/molecules/ResponseTimeChart'),
  {
    ssr: false,
    loading: () => (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }
);

const StatusCodeDistributionChart = dynamic(
  () => import('@/components/molecules/StatusCodeDistributionChart'),
  {
    ssr: false,
    loading: () => (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }
);

export default function TestRunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  const runId = params.run_id as string;
  
  // SWRを使用して直接テスト実行結果を取得
  const { testRun, isLoading: isLoadingRun } = useTestRunDetail(serviceId, runId);
  const { services } = useServices();
  const { testCases, isLoading: isLoadingTestCases } = useTestCases(serviceId);
  
  // テストスイートの詳細を取得
  const suiteId = testRun?.suite_id;
  const { testSuite, isLoading: isLoadingSuite } = useTestSuiteDetail(serviceId, suiteId ?? null);

  // 選択されたテストケース結果
  const [selectedCaseResult, setSelectedCaseResult] = React.useState<TestCaseResult | null>(null);
  
  const service = React.useMemo(() => {
    if (!services) return null;
    return services.find((p: Service) => p.id === serviceId);
  }, [services, serviceId]);

  // 全ステップ結果を取得
  const allStepResults = React.useMemo(() => {
    if (!testRun?.test_case_results) return [];
    return testRun.test_case_results.flatMap(caseResult => caseResult.step_results || []);
  }, [testRun?.test_case_results]);

  // 選択されたケースのステップ結果
  const selectedStepResults = React.useMemo(() => {
    if (!selectedCaseResult) return [];
    return selectedCaseResult.step_results || [];
  }, [selectedCaseResult]);

  // テストケース名を取得
  const getTestCaseName = (caseId: string) => {
    if (!testSuite?.test_cases) return '不明なテストケース';
    const testCase = testSuite.test_cases.find(tc => tc.id === caseId);
    return testCase?.name || '名前なし';
  };

  if (isLoadingRun || isLoadingTestCases || isLoadingSuite) {
    return <div className="text-center py-8">読み込み中...</div>;
  }
  
  if (!service || !testRun) {
    return (
      <div className="text-center py-8">
        <p>テスト実行が見つかりません</p>
        <Button asChild className="mt-4">
          <Link href={`/projects/${serviceId}/runs`}>テスト実行一覧に戻る</Link>
        </Button>
      </div>
    );
  }

  // テストケース結果の詳細を表示するダイアログを開く
  const handleViewDetails = (caseResult: TestCaseResult) => {
    setSelectedCaseResult(caseResult);
    const dialog = document.getElementById('test-case-detail-dialog');
    if (dialog instanceof HTMLDialogElement) {
      dialog.showModal();
    }
  };

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
          <Link href={`/projects/${serviceId}/runs`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            テスト実行一覧に戻る
          </Link>
        </Button>
      </div>
      
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">テスト実行 #{runId}</h1>
        <div className="flex items-center gap-2">
          {testRun.status === 'completed' ? (
            <div className="flex items-center text-green-500 gap-1">
              <CheckCircleIcon className="h-5 w-5" />
              <span>完了</span>
            </div>
          ) : testRun.status === 'failed' ? (
            <div className="flex items-center text-red-500 gap-1">
              <XCircleIcon className="h-5 w-5" />
              <span>失敗</span>
            </div>
          ) : (
            <div className="flex items-center text-yellow-500 gap-1">
              <ClockIcon className="h-5 w-5" />
              <span>実行中</span>
            </div>
          )}
        </div>
      </div>
      
      <Tabs defaultValue="summary" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="summary" className="flex items-center gap-2">
            <ListIcon className="h-4 w-4" />
            <span>概要</span>
          </TabsTrigger>
          <TabsTrigger value="results" className="flex items-center gap-2">
            <CheckCircleIcon className="h-4 w-4" />
            <span>結果詳細</span>
          </TabsTrigger>
          <TabsTrigger value="charts" className="flex items-center gap-2">
            <BarChart3Icon className="h-4 w-4" />
            <span>グラフ</span>
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="summary" className="mt-6 space-y-6">
          <TestRunSummary 
            testRun={testRun} 
            serviceName={service.name} 
          />
        </TabsContent>
        
        <TabsContent value="results" className="mt-6 space-y-6">
          <TestCaseResultList 
            testCaseResults={testRun.test_case_results || []} 
            testCases={testSuite?.test_cases || []}
            onViewDetails={handleViewDetails}
          />
          
          <dialog
            id="test-case-detail-dialog"
            className="p-0 rounded-lg shadow-lg backdrop:bg-black/50 w-full max-w-4xl"
          >
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">
                  {selectedCaseResult && getTestCaseName(selectedCaseResult.case_id)}
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const dialog = document.getElementById('test-case-detail-dialog');
                    if (dialog instanceof HTMLDialogElement) {
                      dialog.close();
                    }
                  }}
                >
                  ✕
                </Button>
              </div>
              
              {selectedCaseResult && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex justify-between">
                      <span className="font-medium">ステータス</span>
                      <span className={`
                        ${selectedCaseResult.status === 'passed' ? 'text-green-500' : 
                          selectedCaseResult.status === 'failed' ? 'text-red-500' : 
                          'text-yellow-500'}
                      `}>
                        {selectedCaseResult.status === 'passed' ? '成功' : 
                         selectedCaseResult.status === 'failed' ? '失敗' : 
                         'スキップ'}
                      </span>
                    </div>
                    {selectedCaseResult.error_message && (
                      <div className="col-span-2">
                        <span className="font-medium text-red-500">エラーメッセージ:</span>
                        <div className="bg-muted p-2 rounded-md overflow-auto max-h-24 text-red-500 mt-1">
                          <pre className="font-mono text-sm whitespace-pre-wrap">{selectedCaseResult.error_message}</pre>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <TestStepResultList 
                    stepResults={selectedStepResults} 
                    testCaseName={getTestCaseName(selectedCaseResult.case_id)}
                  />
                </div>
              )}
            </div>
          </dialog>
        </TabsContent>
        
        <TabsContent value="charts" className="mt-6 space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <SuccessRateChart testCaseResults={testRun.test_case_results || []} />
            <StatusCodeDistributionChart stepResults={allStepResults} />
          </div>
          <ResponseTimeChart stepResults={allStepResults} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
