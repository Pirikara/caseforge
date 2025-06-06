"use client"

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ArrowLeftIcon, Trash2Icon, EditIcon } from 'lucide-react';
import { useTestSuiteDetail } from '@/hooks/useTestChains';
import { useTestCases } from '@/hooks/useTestCases';
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
import { toast } from 'sonner';
import { fetcher } from '@/utils/fetcher';

export default function TestSuiteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  const suiteId = params.suite_id as string;

  const { testSuite, isLoading: isLoadingSuite, error: errorSuite } = useTestSuiteDetail(serviceId, suiteId);
  const { testCases, isLoading: isLoadingTestCases, error: errorTestCases } = useTestCases(serviceId);

  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);

  const suiteTestCases = React.useMemo(() => {
    if (!testSuite || !testCases) return [];
    const testCaseIdsInSuite = new Set(testSuite.test_cases?.map(tc => tc.id));
    return testCases.filter(tc => testCaseIdsInSuite.has(tc.id));
  }, [testSuite, testCases]);

  const handleDeleteSuite = async () => {
    setIsDeleting(true);
    try {
      await fetcher(`/api/services/${serviceId}/test-suites/${suiteId}`, 'DELETE');
      toast.success('テストスイートが削除されました。');
      router.push(`/services/${serviceId}/test-suites`);
    } catch (error: any) {
      toast.error('テストスイートの削除に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };


  if (isLoadingSuite || isLoadingTestCases) {
    return <div className="text-center py-8">読み込み中...</div>;
  }

  if (errorSuite) {
    return <div className="text-center py-8 text-red-500">テストスイートの読み込み中にエラーが発生しました: {errorSuite.message}</div>;
  }

  if (!testSuite) {
    return (
      <div className="text-center py-8">
        <p>テストスイートが見つかりません</p>
        <Button asChild className="mt-4">
          <Link href={`/services/${serviceId}/test-suites`}>テストスイート一覧に戻る</Link>
        </Button>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6">
        <div className="flex items-center gap-2 mb-4">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/services/${serviceId}/test-suites`}>
              <ArrowLeftIcon className="h-4 w-4 mr-1" />
              テストスイート一覧に戻る
            </Link>
          </Button>
        </div>

        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">テストスイート: {testSuite.name}</h1>
          <div>
             <Button variant="outline" size="sm" className="mr-2" asChild>
               <Link href={`/services/${serviceId}/test-suites/${suiteId}/edit`}>
                 <EditIcon className="h-4 w-4 mr-1" />編集
               </Link>
             </Button>
             <Button
               variant="destructive"
               size="sm"
               onClick={() => setShowDeleteDialog(true)}
               disabled={isDeleting}
             >
               {isDeleting ? '削除中...' : <><Trash2Icon className="h-4 w-4 mr-1" />削除</>}
             </Button>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>テストスイート情報</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4">
              <div className="flex justify-between">
                <dt className="font-medium">ID</dt>
                <dd className="text-muted-foreground">{testSuite.id}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">名前</dt>
                <dd className="text-muted-foreground">{testSuite.name}</dd>
              </div>
               <div className="flex justify-between">
                <dt className="font-medium">対象メソッド</dt>
                <dd className="text-muted-foreground">{testSuite.target_method}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">対象パス</dt>
                <dd className="text-muted-foreground">{testSuite.target_path}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">テストケース数</dt>
                <dd className="text-muted-foreground">{suiteTestCases.length}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <div className="flex justify-between items-center">
             <h2 className="text-xl font-semibold">テストケース一覧</h2>
             <Button asChild>
               <Link href={`/services/${serviceId}/tests/new?suiteId=${suiteId}`}>
                 新規テストケース作成
               </Link>
             </Button>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>テストケース</CardTitle>
            </CardHeader>
            <CardContent>
              {suiteTestCases.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名前</TableHead>
                      <TableHead>対象メソッド</TableHead>
                      <TableHead>対象パス</TableHead>
                      <TableHead className="w-[100px]">アクション</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {suiteTestCases.map((testCase) => (
                      <TableRow key={testCase.id}>
                        <TableCell className="font-medium">{testCase.title || '名前なし'}</TableCell>
                        <TableCell>{testCase.method}</TableCell>
                        <TableCell>{testCase.path}</TableCell>
                        <TableCell>
                          <Button variant="outline" size="sm" asChild>
                            <Link href={`/services/${serviceId}/tests/${testCase.id}`}>
                              詳細
                            </Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">このテストスイートにはまだテストケースがありません。</p>
                  <Button asChild className="mt-4">
                    <Link href={`/services/${serviceId}/tests/new?suiteId=${suiteId}`}>
                      新規テストケース作成
                    </Link>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>テストスイートを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は元に戻せません。テストスイートに関連する全てのデータ（テストケース、実行結果など）が完全に削除されます。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>キャンセル</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteSuite} disabled={isDeleting}>
              {isDeleting ? '削除中...' : '削除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
