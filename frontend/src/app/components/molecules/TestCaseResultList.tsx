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
import { Input } from '@/components/ui/input';
import { SearchIcon, CheckCircleIcon, XCircleIcon } from 'lucide-react';
import { TestCaseResult, TestCase } from '@/hooks/useTestRuns';

interface TestCaseResultListProps {
  testCaseResults: TestCaseResult[];
  testCases: TestCase[];
  onViewDetails: (caseResult: TestCaseResult) => void;
}

export default function TestCaseResultList({ 
  testCaseResults, 
  testCases, 
  onViewDetails 
}: TestCaseResultListProps) {
  const [searchQuery, setSearchQuery] = React.useState('');
  
  // 検索フィルタリング
  const filteredResults = React.useMemo(() => {
    if (!testCaseResults || !testCases) return [];
    
    return testCaseResults.filter(caseResult => {
      // TestCaseResult の case_id に対応する TestCase を取得
      const testCase = testCases.find(testCase => testCase.id === caseResult.case_id);
      if (!testCase) return false; // テストケース情報が見つからない場合はスキップ
      
      // 検索フィルター
      const lowerCaseQuery = searchQuery.toLowerCase();
      return (
        (testCase.name?.toLowerCase().includes(lowerCaseQuery)) ||
        (testCase.description?.toLowerCase().includes(lowerCaseQuery)) ||
        (testCase.target_path?.toLowerCase().includes(lowerCaseQuery)) ||
        (testCase.target_method?.toLowerCase().includes(lowerCaseQuery))
      );
    });
  }, [testCaseResults, testCases, searchQuery]);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">テストケース結果</h2>
        <div className="relative w-64">
          <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="テストケースを検索..."
            className="pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      
      {filteredResults.length > 0 ? (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[80px]">結果</TableHead>
                <TableHead className="w-[80px]">メソッド</TableHead>
                <TableHead>テストケース</TableHead>
                <TableHead className="w-[200px]">パス</TableHead>
                <TableHead className="w-[100px]">ステータス</TableHead>
                <TableHead className="w-[100px]">アクション</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredResults.map((caseResult) => {
                // TestCaseResult の case_id に対応する TestCase を取得
                const testCase = testCases.find(testCase => testCase.id === caseResult.case_id);
                if (!testCase) return null; // テストケース情報が見つからない場合はスキップ
                
                return (
                  <TableRow key={caseResult.id}>
                    <TableCell>
                      {caseResult.status === 'passed' ? (
                        <CheckCircleIcon className="h-5 w-5 text-green-500" />
                      ) : caseResult.status === 'failed' ? (
                        <XCircleIcon className="h-5 w-5 text-red-500" />
                      ) : (
                        <span className="h-5 w-5 flex items-center justify-center text-yellow-500">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        testCase.target_method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200' :
                        testCase.target_method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200' :
                        testCase.target_method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200' :
                        testCase.target_method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200' :
                        'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200'
                      }`}>
                        {testCase.target_method}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{testCase.name || '名前なし'}</div>
                      {testCase.description && (
                        <div className="text-xs text-muted-foreground truncate max-w-[200px]">
                          {testCase.description}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      <div className="truncate max-w-[200px]">
                        {testCase.target_path}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={`
                        ${caseResult.status === 'passed' ? 'text-green-500' : 
                          caseResult.status === 'failed' ? 'text-red-500' : 
                          'text-yellow-500'}
                      `}>
                        {caseResult.status === 'passed' ? '成功' : 
                         caseResult.status === 'failed' ? '失敗' : 
                         'スキップ'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onViewDetails(caseResult)}
                      >
                        詳細
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      ) : (
        <div className="text-center py-8 border rounded-lg bg-background">
          <p className="text-muted-foreground">テスト結果が見つかりません</p>
          {searchQuery ? (
            <p className="mt-2">検索条件を変更してください</p>
          ) : (
            <p className="mt-2">テスト実行が完了していないか、結果がありません</p>
          )}
        </div>
      )}
    </div>
  );
}
