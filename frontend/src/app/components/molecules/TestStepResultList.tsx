"use client"

import React from 'react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CheckCircleIcon, XCircleIcon } from 'lucide-react';
import { StepResult } from '@/hooks/useTestRuns';

interface TestStepResultListProps {
  stepResults: StepResult[];
  testCaseName?: string;
}

export default function TestStepResultList({ 
  stepResults,
  testCaseName
}: TestStepResultListProps) {
  const formatJSON = (json: any) => {
    try {
      return JSON.stringify(json, null, 2);
    } catch (e) {
      return String(json);
    }
  };

  const sortedStepResults = React.useMemo(() => {
    if (!stepResults) return [];
    return [...stepResults].sort((a, b) => a.sequence - b.sequence);
  }, [stepResults]);

  return (
    <div className="space-y-4">
      {testCaseName && (
        <h3 className="text-lg font-semibold">{testCaseName}</h3>
      )}
      
      {sortedStepResults.length > 0 ? (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[60px]">順序</TableHead>
                <TableHead className="w-[80px]">結果</TableHead>
                <TableHead className="w-[80px]">メソッド</TableHead>
                <TableHead>パス</TableHead>
                <TableHead className="w-[100px]">ステータス</TableHead>
                <TableHead className="w-[120px]">レスポンス時間</TableHead>
                <TableHead className="w-[100px]">アクション</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedStepResults.map((stepResult) => (
                <TableRow key={stepResult.id}>
                  <TableCell className="font-medium">
                    {stepResult.sequence}
                  </TableCell>
                  <TableCell>
                    {stepResult.passed ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircleIcon className="h-5 w-5 text-red-500" />
                    )}
                  </TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      stepResult.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200' :
                      stepResult.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200' :
                      stepResult.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200' :
                      stepResult.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200' :
                      'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200'
                    }`}>
                      {stepResult.method}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    <div className="truncate max-w-[200px]">
                      {stepResult.path}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className={stepResult.passed ? 'text-green-500' : 'text-red-500'}>
                      {stepResult.status_code || 'N/A'}
                    </span>
                  </TableCell>
                  <TableCell>
                    {stepResult.response_time !== undefined ? 
                      `${stepResult.response_time.toFixed(2)} ms` : 'N/A'}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const dialog = document.getElementById(`step-result-dialog-${stepResult.id}`);
                        if (dialog instanceof HTMLDialogElement) {
                          dialog.showModal();
                        }
                      }}
                    >
                      詳細
                    </Button>
                    
                    <dialog
                      id={`step-result-dialog-${stepResult.id}`}
                      className="p-0 rounded-lg shadow-lg backdrop:bg-black/50 w-full max-w-3xl"
                    >
                      <div className="p-6">
                        <div className="flex justify-between items-center mb-4">
                          <h3 className="text-lg font-semibold">ステップ実行結果詳細</h3>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const dialog = document.getElementById(`step-result-dialog-${stepResult.id}`);
                              if (dialog instanceof HTMLDialogElement) {
                                dialog.close();
                              }
                            }}
                          >
                            ✕
                          </Button>
                        </div>
                        
                        <div className="grid gap-4">
                          <div className="flex justify-between">
                            <span className="font-medium">ステップ順序</span>
                            <span>{stepResult.sequence}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="font-medium">メソッド</span>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              stepResult.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200' :
                              stepResult.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200' :
                              stepResult.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200' :
                              stepResult.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200' :
                              'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200'
                            }`}>
                              {stepResult.method}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="font-medium">パス</span>
                            <span className="font-mono">{stepResult.path}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="font-medium">結果</span>
                            <span className={stepResult.passed ? 'text-green-500' : 'text-red-500'}>
                              {stepResult.passed ? '成功' : '失敗'}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="font-medium">ステータスコード</span>
                            <span>{stepResult.status_code || 'N/A'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="font-medium">レスポンス時間</span>
                            <span>{stepResult.response_time !== undefined ? `${stepResult.response_time.toFixed(2)} ms` : 'N/A'}</span>
                          </div>
                          
                          {stepResult.error_message && (
                            <div className="space-y-1">
                              <span className="font-medium text-red-500">エラーメッセージ:</span>
                              <div className="bg-muted p-2 rounded-md overflow-auto max-h-24 text-red-500">
                                <pre className="font-mono text-sm whitespace-pre-wrap">{stepResult.error_message}</pre>
                              </div>
                            </div>
                          )}

                          {stepResult.extracted_values && Object.keys(stepResult.extracted_values).length > 0 && (
                            <div className="space-y-1">
                              <span className="font-medium">抽出された値:</span>
                              <div className="bg-muted p-2 rounded-md overflow-auto max-h-24">
                                <pre className="font-mono text-sm whitespace-pre-wrap">{formatJSON(stepResult.extracted_values)}</pre>
                              </div>
                            </div>
                          )}

                          <Tabs defaultValue="response" className="mt-2">
                            <TabsList className="grid w-full grid-cols-2">
                              <TabsTrigger value="request">リクエスト</TabsTrigger>
                              <TabsTrigger value="response">レスポンス</TabsTrigger>
                            </TabsList>
                            <TabsContent value="request" className="mt-2">
                              <div className="bg-muted p-4 rounded-md overflow-auto max-h-60">
                                <pre className="font-mono text-sm whitespace-pre-wrap">
                                  {'リクエストボディ情報は利用できません'}
                                </pre>
                              </div>
                            </TabsContent>
                            <TabsContent value="response" className="mt-2">
                              <div className="bg-muted p-4 rounded-md overflow-auto max-h-60">
                                <pre className="font-mono text-sm whitespace-pre-wrap">
                                  {stepResult.response_body ? formatJSON(stepResult.response_body) : 'レスポンスボディなし'}
                                </pre>
                              </div>
                            </TabsContent>
                          </Tabs>
                        </div>
                      </div>
                    </dialog>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        <div className="text-center py-8 border rounded-lg bg-background">
          <p className="text-muted-foreground">ステップ結果が見つかりません</p>
        </div>
      )}
    </div>
  );
}
