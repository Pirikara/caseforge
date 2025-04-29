"use client"

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { SearchIcon, FileTextIcon, XIcon } from 'lucide-react';
import { toast } from 'sonner';
import { useEndpoints, Endpoint } from '@/hooks/useEndpoints';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetClose,
} from '@/components/ui/sheet';

export const EndpointManagementTab = ({ projectId }: { projectId: string }) => {
  const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
  const { endpoints, isLoading, mutate } = useEndpoints(projectId);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedEndpoints, setSelectedEndpoints] = React.useState<string[]>([]);
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [selectedEndpoint, setSelectedEndpoint] = React.useState<Endpoint | null>(null);
  const [isDetailOpen, setIsDetailOpen] = React.useState(false);
  
  
  // 検索フィルタリング（メモ化）
  const filteredEndpoints = React.useMemo(() => {
    if (!endpoints) return [];
    
    if (!searchQuery) return endpoints;
    
    const query = searchQuery.toLowerCase();
    return endpoints.filter(endpoint =>
      endpoint.path.toLowerCase().includes(query) ||
      endpoint.method.toLowerCase().includes(query) ||
      endpoint.summary?.toLowerCase().includes(query) ||
      endpoint.description?.toLowerCase().includes(query)
    );
  }, [endpoints, searchQuery]);
  
  // すべて選択/解除
  const toggleSelectAll = () => {
    if (selectedEndpoints.length === filteredEndpoints.length) {
      setSelectedEndpoints([]);
    } else {
      setSelectedEndpoints(filteredEndpoints.map(e => e.id));
    }
  };
  
  // 個別のエンドポイント選択/解除
  const toggleEndpoint = (id: string) => {
    if (selectedEndpoints.includes(id)) {
      setSelectedEndpoints(selectedEndpoints.filter(eId => eId !== id));
    } else {
      setSelectedEndpoints([...selectedEndpoints, id]);
    }
  };

  // エンドポイント詳細表示時のデバッグログ
  React.useEffect(() => {
    if (selectedEndpoint) {
      console.log('選択されたエンドポイント詳細:', {
        id: selectedEndpoint.id,
        path: selectedEndpoint.path,
        method: selectedEndpoint.method,
        request_body: selectedEndpoint.request_body,
        request_headers: selectedEndpoint.request_headers,
        request_query_params: selectedEndpoint.request_query_params,
        responses: selectedEndpoint.responses
      });
    }
  }, [selectedEndpoint]);
  
  // テストチェーン生成
  const handleGenerateChain = async () => {
    if (selectedEndpoints.length === 0) {
      toast.error('エンドポイントが選択されていません');
      return;
    }
    
    try {
      setIsGenerating(true);
      
      // URLの構築方法を修正
      const response = await fetch(`${API}/api/projects/${projectId}/endpoints/generate-chain`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          endpoint_ids: selectedEndpoints,
        }),
      });
      
      // デバッグ情報を追加
      console.log('テストチェーン生成APIレスポンス:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries([...response.headers.entries()])
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'テストチェーン生成に失敗しました');
      }
      
      const data = await response.json();
      
      toast.success('テストチェーン生成タスクが開始されました', {
        description: 'バックグラウンドでテストチェーン生成が実行されています。しばらくしてからテストチェーン一覧を確認してください。',
      });
      
      // テストチェーン管理タブに自動遷移
      document.querySelector('[data-value="test-chains"]')?.dispatchEvent(
        new MouseEvent('click', { bubbles: true })
      );
    } catch (error) {
      console.error('テストチェーン生成エラー:', error);
      
      toast.error('エラーが発生しました', {
        description: error instanceof Error ? error.message : '不明なエラーが発生しました',
      });
    } finally {
      setIsGenerating(false);
    }
  };
  
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>エンドポイント一覧</CardTitle>
          <CardDescription>
            OpenAPIスキーマから抽出されたエンドポイントの一覧です。テストチェーンを生成するエンドポイントを選択してください。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="relative flex-1">
              <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="エンドポイントを検索..."
                className="pl-8"
                value={searchQuery}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="select-all"
                checked={filteredEndpoints.length > 0 && selectedEndpoints.length === filteredEndpoints.length}
                onCheckedChange={toggleSelectAll}
              />
              <label htmlFor="select-all" className="text-sm">すべて選択</label>
            </div>
          </div>
          
          {isLoading ? (
            <div className="text-center py-8">読み込み中...</div>
          ) : filteredEndpoints.length > 0 ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]"></TableHead>
                    <TableHead className="w-[100px]">メソッド</TableHead>
                    <TableHead className="w-[300px]">パス</TableHead>
                    <TableHead>概要</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredEndpoints.map((endpoint) => (
                    <TableRow
                      key={endpoint.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => {
                        setSelectedEndpoint(endpoint);
                        setIsDetailOpen(true);
                      }}
                    >
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Checkbox
                          checked={selectedEndpoints.includes(endpoint.id)}
                          onCheckedChange={() => toggleEndpoint(endpoint.id)}
                        />
                      </TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          endpoint.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                          endpoint.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                          endpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                          endpoint.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                          'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
                        }`}>
                          {endpoint.method}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{endpoint.path}</TableCell>
                      <TableCell>{endpoint.summary || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8 border rounded-lg bg-background">
              <p className="text-muted-foreground">エンドポイントが見つかりません</p>
              {searchQuery ? (
                <p className="mt-2">検索条件を変更してください</p>
              ) : (
                <p className="mt-2">スキーマをアップロードしてエンドポイントを抽出してください</p>
              )}
            </div>
          )}
          
          {filteredEndpoints.length > 0 && (
            <div className="flex justify-end">
              <Button
                onClick={handleGenerateChain}
                disabled={isGenerating || selectedEndpoints.length === 0}
              >
                <FileTextIcon className="h-4 w-4 mr-2" />
                {isGenerating ? 'テストチェーン生成中...' : `選択したエンドポイントからテストチェーン生成 (${selectedEndpoints.length}件)`}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* エンドポイント詳細表示用のサイドパネル */}
      <Sheet open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
          <SheetHeader className="mb-6 pb-4 border-b">
            <div className="flex items-center justify-between">
              <SheetTitle className="text-xl font-bold">エンドポイント詳細</SheetTitle>
              <SheetClose className="rounded-full hover:bg-muted p-2 transition-colors">
                <XIcon className="h-4 w-4" />
              </SheetClose>
            </div>
            <SheetDescription>
              {selectedEndpoint && (
                <div className="flex items-center gap-3 mt-2">
                  <span className={`px-3 py-1.5 rounded-md text-xs font-bold tracking-wide ${
                    selectedEndpoint.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                    selectedEndpoint.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                    selectedEndpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                    selectedEndpoint.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                    'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
                  }`}>
                    {selectedEndpoint.method}
                  </span>
                  <span className="font-mono text-sm font-medium">{selectedEndpoint.path}</span>
                </div>
              )}
            </SheetDescription>
          </SheetHeader>

          {selectedEndpoint && (
            <div className="space-y-8">
              {/* 概要と説明 */}
              {(selectedEndpoint.summary || selectedEndpoint.description) && (
                <div className="bg-card rounded-lg p-4 shadow-sm">
                  <h3 className="text-lg font-semibold mb-3 text-primary">概要</h3>
                  {selectedEndpoint.summary && <p className="mb-3 font-medium">{selectedEndpoint.summary}</p>}
                  {selectedEndpoint.description && <p className="text-sm text-muted-foreground">{selectedEndpoint.description}</p>}
                </div>
              )}

              {/* リクエストパラメータ */}
              {selectedEndpoint.request_query_params && typeof selectedEndpoint.request_query_params === 'object' && Object.keys(selectedEndpoint.request_query_params).length > 0 && (
                <div className="bg-card rounded-lg p-4 shadow-sm">
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2 text-primary">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-search">
                      <circle cx="11" cy="11" r="8"></circle>
                      <path d="m21 21-4.3-4.3"></path>
                    </svg>
                    クエリパラメータ
                  </h3>
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/50">
                          <TableHead className="font-semibold">パラメータ名</TableHead>
                          <TableHead className="font-semibold">必須</TableHead>
                          <TableHead className="font-semibold">型</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(selectedEndpoint.request_query_params).map(([name, param]: [string, any]) => (
                          <TableRow key={name} className="hover:bg-muted/30">
                            <TableCell className="font-medium text-primary">{name}</TableCell>
                            <TableCell>{param.required ?
                              <span className="text-green-600 dark:text-green-400 font-medium">✓</span> :
                              <span className="text-muted-foreground">-</span>}
                            </TableCell>
                            <TableCell>
                              <span className="px-2 py-1 bg-muted rounded text-xs">
                                {param.schema?.type || '-'}
                              </span>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}

              {/* リクエストヘッダー */}
              {selectedEndpoint.request_headers && typeof selectedEndpoint.request_headers === 'object' && Object.keys(selectedEndpoint.request_headers).length > 0 && (
                <div className="bg-card rounded-lg p-4 shadow-sm">
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2 text-primary">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-file-text">
                      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
                      <polyline points="14 2 14 8 20 8"></polyline>
                      <line x1="16" x2="8" y1="13" y2="13"></line>
                      <line x1="16" x2="8" y1="17" y2="17"></line>
                      <line x1="10" x2="8" y1="9" y2="9"></line>
                    </svg>
                    リクエストヘッダー
                  </h3>
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/50">
                          <TableHead className="font-semibold">ヘッダー名</TableHead>
                          <TableHead className="font-semibold">必須</TableHead>
                          <TableHead className="font-semibold">説明</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(selectedEndpoint.request_headers).map(([name, header]: [string, any]) => (
                          <TableRow key={name} className="hover:bg-muted/30">
                            <TableCell className="font-medium text-primary">{name}</TableCell>
                            <TableCell>{header.required ?
                              <span className="text-green-600 dark:text-green-400 font-medium">✓</span> :
                              <span className="text-muted-foreground">-</span>}
                            </TableCell>
                            <TableCell>{header.schema?.description || '-'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}

              {/* リクエストボディ */}
              {selectedEndpoint.request_body && typeof selectedEndpoint.request_body === 'object' && (
                <div className="bg-card rounded-lg p-4 shadow-sm">
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2 text-primary">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-code">
                      <polyline points="16 18 22 12 16 6"></polyline>
                      <polyline points="8 6 2 12 8 18"></polyline>
                    </svg>
                    リクエストボディ
                  </h3>
                  <div className="border rounded-md p-4 bg-muted/30 overflow-auto">
                    <pre className="text-xs whitespace-pre-wrap font-mono">
                      {JSON.stringify(selectedEndpoint.request_body, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* レスポンス */}
              {selectedEndpoint.responses && typeof selectedEndpoint.responses === 'object' && Object.keys(selectedEndpoint.responses).length > 0 && (
                <div className="bg-card rounded-lg p-4 shadow-sm">
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2 text-primary">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-arrow-left-right">
                      <path d="m8 3-6 6 6 6"></path>
                      <path d="m16 3 6 6-6 6"></path>
                      <line x1="3" x2="21" y1="9" y2="9"></line>
                    </svg>
                    レスポンス
                  </h3>
                  <div className="space-y-4">
                    {Object.entries(selectedEndpoint.responses).map(([status, response]: [string, any]) => (
                      <div key={status} className="border rounded-md p-4 hover:bg-muted/20 transition-colors">
                        <h4 className="font-semibold mb-2 flex items-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            status.startsWith('2') ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                            status.startsWith('4') ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300' :
                            status.startsWith('5') ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
                            'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
                          }`}>
                            {status}
                          </span>
                          <span>{response.description || 'レスポンス'}</span>
                        </h4>
                        {response.content && response.content['application/json']?.schema && (
                          <div className="mt-3">
                            <h5 className="text-sm font-medium mb-2">スキーマ:</h5>
                            <div className="bg-muted/30 p-3 rounded-md overflow-auto border">
                              <pre className="text-xs whitespace-pre-wrap font-mono">
                                {JSON.stringify(response.content['application/json'].schema, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default EndpointManagementTab;