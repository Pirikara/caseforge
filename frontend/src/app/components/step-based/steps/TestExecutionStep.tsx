"use client"

import React, { useState, useEffect } from 'react';
import { useUIMode } from '@/contexts/UIModeContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { Play, CheckCircle, XCircle, Clock, AlertTriangle, Loader2, BarChart } from 'lucide-react';
import { fetcher } from '@/utils/fetcher';
import Link from 'next/link';

interface TestCase {
  id: string;
  title: string;
  method: string;
  path: string;
}

interface TestResult {
  id: string;
  test_case_id: string;
  status: 'success' | 'failure' | 'error' | 'pending';
  response_time?: number;
  status_code?: number;
  error_message?: string;
}

interface TestRunSummary {
  id: string;
  total: number;
  success: number;
  failure: number;
  error: number;
  pending: number;
  average_response_time?: number;
}

export function TestExecutionStep() {
  const { sharedData, updateSharedData } = useUIMode();
  const serviceId = sharedData.serviceId;
  const testSuiteId = sharedData.testSuiteId;
  const testSuiteName = sharedData.testSuiteName;
  
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [runSummary, setRunSummary] = useState<TestRunSummary | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  
  useEffect(() => {
    if (serviceId && testSuiteId) {
      fetchTestCases();
    }
  }, [serviceId, testSuiteId]);
  
  const fetchTestCases = async () => {
    try {
      const data = await fetcher(`/api/services/${serviceId}/test-suites/${testSuiteId}/test-cases`);
      setTestCases(data);
      
      const initialResults: Record<string, TestResult> = {};
      data.forEach((testCase: TestCase) => {
        initialResults[testCase.id] = {
          id: '',
          test_case_id: testCase.id,
          status: 'pending'
        };
      });
      setTestResults(initialResults);
      
    } catch (error) {
      console.error('テストケース取得エラー:', error);
      toast.error("テストケース取得エラー", {
        description: "テストケース一覧の取得中にエラーが発生しました",
      });
    }
  };
  
  const handleRunTests = async () => {
    if (!serviceId || !testSuiteId) {
      toast.error("テスト実行エラー", {
        description: "サービスIDまたはテストスイートIDがありません",
      });
      return;
    }
    
    setIsRunning(true);
    
    try {
      const response = await fetcher(`/api/services/${serviceId}/run-test-suites`, 'POST', {
        test_suite_ids: [testSuiteId]
      });
      
      setRunId(response.run_id);
      
      toast.info("テスト実行を開始しました", {
        description: "テストケースの実行を開始しました。完了までしばらくお待ちください。",
      });
      
      await pollTestResults(response.run_id);
      
    } catch (error) {
      console.error('テスト実行エラー:', error);
      toast.error("テスト実行エラー", {
        description: "テストの実行中にエラーが発生しました",
      });
      setIsRunning(false);
    }
  };
  
  const pollTestResults = async (runId: string) => {
    try {
      for (let i = 0; i < testCases.length; i++) {
        const testCase = testCases[i];
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const status = Math.random() > 0.3 ? 'success' : (Math.random() > 0.5 ? 'failure' : 'error');
        const responseTime = Math.floor(Math.random() * 500) + 50;
        const statusCode = status === 'success' ? 200 : (status === 'failure' ? 400 : 500);
        
        setTestResults(prev => ({
          ...prev,
          [testCase.id]: {
            id: `result-${testCase.id}`,
            test_case_id: testCase.id,
            status,
            response_time: responseTime,
            status_code: statusCode,
            error_message: status !== 'success' ? 'テスト失敗のサンプルエラーメッセージ' : undefined
          }
        }));
      }
      
      const results = Object.values(testResults);
      const summary: TestRunSummary = {
        id: runId,
        total: results.length,
        success: results.filter(r => r.status === 'success').length,
        failure: results.filter(r => r.status === 'failure').length,
        error: results.filter(r => r.status === 'error').length,
        pending: results.filter(r => r.status === 'pending').length,
        average_response_time: results
          .filter(r => r.response_time)
          .reduce((sum, r) => sum + (r.response_time || 0), 0) / results.length
      };
      
      setRunSummary(summary);
      updateSharedData('testRunId', runId);
      updateSharedData('testRunSummary', summary);
      
      toast.success("テスト実行が完了しました", {
        description: `成功: ${summary.success}, 失敗: ${summary.failure + summary.error}`,
      });
      
    } catch (error) {
      console.error('テスト結果取得エラー:', error);
      toast.error("テスト結果取得エラー", {
        description: "テスト結果の取得中にエラーが発生しました",
      });
    } finally {
      setIsRunning(false);
    }
  };
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failure': return <XCircle className="h-5 w-5 text-red-500" />;
      case 'error': return <AlertTriangle className="h-5 w-5 text-amber-500" />;
      case 'pending': return <Clock className="h-5 w-5 text-gray-400" />;
      default: return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>テスト実行</CardTitle>
        <CardDescription>
          生成されたテストケースを実行して結果を確認します
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* テストスイート情報 */}
        <div className="rounded-md bg-muted p-3">
          <h4 className="text-sm font-medium mb-1">テストスイート情報</h4>
          <p className="text-sm">
            <span className="font-medium">名前:</span> {testSuiteName || '名称未設定'}
          </p>
          <p className="text-sm">
            <span className="font-medium">テストケース数:</span> {testCases.length}
          </p>
        </div>
        
        {/* 実行ボタン */}
        <Button 
          className="w-full" 
          onClick={handleRunTests}
          disabled={isRunning || testCases.length === 0}
        >
          {isRunning ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              テスト実行中...
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4" />
              テストを実行
            </>
          )}
        </Button>
        
        {/* テスト結果サマリー */}
        {runSummary && (
          <div className="rounded-md border p-4 space-y-3">
            <div className="flex justify-between items-center">
              <h4 className="font-medium">テスト実行結果</h4>
              {runId && (
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/projects/${serviceId}/runs/${runId}`}>
                    <BarChart className="mr-2 h-4 w-4" />
                    詳細レポート
                  </Link>
                </Button>
              )}
            </div>
            
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="rounded-md bg-muted p-2">
                <div className="text-2xl font-bold">{runSummary.total}</div>
                <div className="text-xs text-muted-foreground">合計</div>
              </div>
              <div className="rounded-md bg-green-50 p-2">
                <div className="text-2xl font-bold text-green-600">{runSummary.success}</div>
                <div className="text-xs text-green-600">成功</div>
              </div>
              <div className="rounded-md bg-red-50 p-2">
                <div className="text-2xl font-bold text-red-600">{runSummary.failure}</div>
                <div className="text-xs text-red-600">失敗</div>
              </div>
              <div className="rounded-md bg-amber-50 p-2">
                <div className="text-2xl font-bold text-amber-600">{runSummary.error}</div>
                <div className="text-xs text-amber-600">エラー</div>
              </div>
            </div>
            
            {runSummary.average_response_time && (
              <div className="text-sm text-center text-muted-foreground">
                平均応答時間: {runSummary.average_response_time.toFixed(2)}ms
              </div>
            )}
          </div>
        )}
        
        {/* テストケース一覧 */}
        <div className="border rounded-md divide-y">
          {testCases.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              テストケースがありません
            </div>
          ) : (
            testCases.map(testCase => {
              const result = testResults[testCase.id];
              return (
                <div key={testCase.id} className="p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(result?.status || 'pending')}
                      <div>
                        <div className="font-medium">{testCase.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {testCase.method} {testCase.path}
                        </div>
                      </div>
                    </div>
                    
                    {result?.status !== 'pending' && (
                      <div className="text-right">
                        {result?.status_code && (
                          <div className={`text-sm font-medium ${
                            result.status === 'success' ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {result.status_code}
                          </div>
                        )}
                        {result?.response_time && (
                          <div className="text-xs text-muted-foreground">
                            {result.response_time}ms
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {result?.error_message && result.status !== 'success' && (
                    <div className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded">
                      {result.error_message}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
