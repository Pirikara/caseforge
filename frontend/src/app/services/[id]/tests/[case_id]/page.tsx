"use client"

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation'; // useRouter をインポート
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ArrowLeftIcon, Trash2Icon, EditIcon } from 'lucide-react'; // Trash2Icon, EditIcon をインポート
import { useTestCaseDetail, TestStep, useTestCases } from '@/hooks/useTestCases'; // テストケース詳細取得用フック, TestStep 型, useTestCases をインポート
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
} from "@/components/ui/alert-dialog"; // AlertDialog コンポーネントをインポート
import { toast } from 'sonner'; // toast をインポート
import { fetcher } from '@/utils/fetcher'; // fetcher をインポート

export default function TestCaseDetailPage() {
  const params = useParams();
  const router = useRouter(); // useRouter を使用
  const serviceId = params.id as string;
  const caseId = params.case_id as string;

  const { testCase, isLoading: isLoadingCase, error: errorCase } = useTestCaseDetail(serviceId, caseId);
  const { deleteChain } = useTestCases(serviceId); // useTestCases から deleteChain をインポート

  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false); // 削除確認ダイアログの表示状態
  const [isDeleting, setIsDeleting] = React.useState(false); // 削除処理中の状態


  // 現状、テストケース詳細にテストステップが含まれていると仮定
  const testSteps = testCase?.steps || [];

  // テストケース削除処理
  const handleDeleteCase = async () => {
    setIsDeleting(true);
    try {
      // useTestCases フックの deleteChain 関数を呼び出す
      await deleteChain(caseId);
       toast.success('テストケースが削除されました。');
       router.push(`/projects/${serviceId}/tests`); // 削除成功後、一覧ページにリダイレクト
     } catch (error: any) {
      toast.error('テストケースの削除に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };


  if (isLoadingCase) {
    return <div className="text-center py-8">読み込み中...</div>;
  }

  if (errorCase) {
    return <div className="text-center py-8 text-red-500">テストケースの読み込み中にエラーが発生しました: {errorCase.message}</div>;
  }

  if (!testCase) {
    return (
      <div className="text-center py-8">
        <p>テストケースが見つかりません</p>
         <Button asChild className="mt-4">
           <Link href={`/projects/${serviceId}/tests`}>テストケース一覧に戻る</Link>
         </Button>
      </div>
    );
  }

  return (
    <> {/* Fragment で囲む */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 mb-4">
           <Button variant="outline" size="sm" asChild>
             <Link href={`/projects/${serviceId}/tests`}>
               <ArrowLeftIcon className="h-4 w-4 mr-1" />
              テストケース一覧に戻る
            </Link>
          </Button>
        </div>

        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">テストケース: {testCase.title || '名前なし'}</h1>
          {/* テストケース編集・削除ボタン */}
          <div>
             <Button variant="outline" size="sm" className="mr-2" asChild> {/* asChild を追加 */}
               <Link href={`/projects/${serviceId}/tests/${caseId}/edit`}> {/* 編集ページへのリンク */}
                 <EditIcon className="h-4 w-4 mr-1" />編集
               </Link>
             </Button>
             <Button
               variant="destructive"
               size="sm"
               onClick={() => setShowDeleteDialog(true)} // 削除ボタンクリックでダイアログ表示
               disabled={isDeleting} // 削除中は無効化
             >
               {isDeleting ? '削除中...' : <><Trash2Icon className="h-4 w-4 mr-1" />削除</>} {/* 削除中の表示 */}
             </Button>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>テストケース情報</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4">
              <div className="flex justify-between">
                <dt className="font-medium">ID</dt>
                <dd className="text-muted-foreground">{testCase.id}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">タイトル</dt>
                <dd className="text-muted-foreground">{testCase.title || '名前なし'}</dd>
              </div>
               <div className="flex justify-between">
                <dt className="font-medium">メソッド</dt>
                <dd className="text-muted-foreground">{testCase.method}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">パス</dt>
                <dd className="text-muted-foreground">{testCase.path}</dd>
              </div>
               <div className="flex justify-between">
                <dt className="font-medium">期待するステータス</dt>
                <dd className="text-muted-foreground">{testCase.expected_status}</dd>
              </div>
               <div className="flex justify-between">
                <dt className="font-medium">目的</dt>
                <dd className="text-muted-foreground">{testCase.purpose}</dd>
              </div>
               <div className="flex justify-between">
                <dt className="font-medium">テストステップ数</dt>
                <dd className="text-muted-foreground">{testSteps.length}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <div className="flex justify-between items-center">
             <h2 className="text-xl font-semibold">テストステップ一覧</h2>
             {/* 新規テストステップ作成ボタン（後で実装） */}
               <Button asChild>
                 <Link href={`/projects/${serviceId}/tests/${caseId}/steps/new`}>
                   新規テストステップ作成
                 </Link>
             </Button>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>テストステップ</CardTitle>
            </CardHeader>
            <CardContent>
              {testSteps.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[80px]">順序</TableHead>
                      <TableHead className="w-[80px]">メソッド</TableHead>
                      <TableHead>パス</TableHead>
                      <TableHead className="w-[120px]">期待するステータス</TableHead>
                      <TableHead className="w-[100px]">アクション</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {testSteps.map((step: TestStep) => (
                      <TableRow key={step.id}>
                        <TableCell>{step.sequence}</TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            step.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200' :
                            step.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200' :
                            step.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200' :
                            step.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200' :
                            'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200'
                          }`}>
                            {step.method}
                          </span>
                        </TableCell>
                        <TableCell className="font-mono text-sm">{step.path}</TableCell>
                        <TableCell>{step.expected_status}</TableCell>
                        <TableCell>
                           <Button variant="outline" size="sm" asChild>
                             <Link href={`/projects/${serviceId}/tests/${caseId}/steps/${step.id}`}>
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
                  <p className="text-muted-foreground">このテストケースにはまだテストステップがありません。</p>
                   {/* 新規テストステップ作成ボタン（後で実装） */}
                   <Button asChild className="mt-4">
                     <Link href={`/projects/${serviceId}/tests/${caseId}/steps/new`}>
                       新規テストステップ作成
                     </Link>
                   </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 削除確認ダイアログ */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>テストケースを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は元に戻せません。テストケースに関連する全てのデータ（テストステップ、実行結果など）が完全に削除されます。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>キャンセル</AlertDialogCancel> {/* 削除中は無効化 */}
            <AlertDialogAction onClick={handleDeleteCase} disabled={isDeleting}> {/* 削除処理を実行 */}
              {isDeleting ? '削除中...' : '削除'} {/* 削除中の表示 */}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
