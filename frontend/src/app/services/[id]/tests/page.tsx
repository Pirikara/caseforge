"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useServices } from '@/hooks/useServices';
import { useTestCases } from '@/hooks/useTestCases';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { SearchIcon, PlayIcon, FileTextIcon, Trash2Icon } from 'lucide-react';

export default function TestCasesPage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  
  const { services } = useServices();
  const { testCases, isLoading, deleteChain } = useTestCases(serviceId);
  
  const [searchQuery, setSearchQuery] = React.useState('');
  const [methodFilter, setMethodFilter] = React.useState('all');
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false);
  const [chainToDelete, setChainToDelete] = React.useState<string | null>(null);
  
  const service = React.useMemo(() => {
    if (!services) return null;
    return services.find(p => p.id === serviceId);
  }, [services, serviceId]);
  
  // 検索とフィルタリング
  const filteredTestCases = React.useMemo(() => {
    if (!testCases) return [];
    
    return testCases.filter(testCase => {
      // 検索フィルター
      const matchesSearch = 
        testCase.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        testCase.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
        testCase.purpose.toLowerCase().includes(searchQuery.toLowerCase());
      
      // メソッドフィルター
      const matchesMethod = methodFilter === 'all' || testCase.method === methodFilter;
      
      return matchesSearch && matchesMethod;
    });
  }, [testCases, searchQuery, methodFilter]);
  
  if (!service) {
    return (
      <div className="text-center py-8">
        <p>サービスが見つかりません</p>
      </div>
    );
  }
  
  return (
    <>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">テストケース一覧</h1>
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link href={`/services/${serviceId}`}>
                <FileTextIcon className="h-4 w-4 mr-2" />
                サービス詳細
              </Link>
            </Button>
            <Button asChild>
              <Link href={`/services/${serviceId}/run`}>
                <PlayIcon className="h-4 w-4 mr-2" />
                テスト実行
              </Link>
            </Button>
          </div>
        </div>
        
        <div className="flex flex-col md:flex-row gap-4 items-end">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="テストケースを検索..."
              className="pl-8"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="w-full md:w-[200px]">
            <Select
              value={methodFilter}
              onValueChange={setMethodFilter}
            >
              <SelectTrigger>
                <SelectValue placeholder="HTTPメソッド" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">すべてのメソッド</SelectItem>
                <SelectItem value="GET">GET</SelectItem>
                <SelectItem value="POST">POST</SelectItem>
                <SelectItem value="PUT">PUT</SelectItem>
                <SelectItem value="DELETE">DELETE</SelectItem>
                <SelectItem value="PATCH">PATCH</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        
        {isLoading ? (
          <div className="text-center py-8">読み込み中...</div>
        ) : filteredTestCases.length > 0 ? (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[300px]">タイトル</TableHead>
                  <TableHead className="w-[80px]">メソッド</TableHead>
                  <TableHead>パス</TableHead>
                  <TableHead className="w-[120px]">期待するステータス</TableHead>
                  <TableHead className="w-[100px]">アクション</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTestCases.map((testCase) => (
                  <TableRow key={testCase.id}>
                    <TableCell className="font-medium">
                      <Link href={`/projects/${serviceId}/tests/${testCase.case_id}`} className="hover:underline">
                        {testCase.title}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        testCase.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200' :
                        testCase.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200' :
                        testCase.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200' :
                        testCase.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200' :
                        'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200'
                      }`}>
                        {testCase.method}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{testCase.path}</TableCell>
                    <TableCell>{testCase.expected_status}</TableCell>
                    <TableCell className="flex space-x-2">
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/projects/${serviceId}/tests/${testCase.case_id}`}>
                          詳細
                        </Link>
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          setChainToDelete(testCase.case_id);
                          setShowDeleteDialog(true);
                        }}
                      >
                        <Trash2Icon className="h-4 w-4 mr-2" />
                        削除
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <div className="text-center py-8 border rounded-lg bg-background">
            <p className="text-muted-foreground">テストケースが見つかりません</p>
            {searchQuery || methodFilter !== 'all' ? (
              <p className="mt-2">検索条件を変更してください</p>
            ) : (
              <p className="mt-2">テスト生成を実行してください</p>
            )}
          </div>
        )}
      </div>
      
      {/* 削除確認ダイアログ */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>テストチェーンを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は元に戻せません。テストチェーンに関連する全てのデータ（実行結果など）が完全に削除されます。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (chainToDelete) {
                  await deleteChain(chainToDelete);
                  setChainToDelete(null);
                  setShowDeleteDialog(false);
                }
              }}
            >
              削除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
