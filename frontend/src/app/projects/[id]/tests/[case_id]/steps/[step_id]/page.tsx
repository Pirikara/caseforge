"use client"

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation'; // useRouter をインポート
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeftIcon, Trash2Icon, EditIcon } from 'lucide-react'; // Trash2Icon, EditIcon をインポート
import { useTestCaseDetail, TestStep } from '@/hooks/useTestCases'; // TestStep 型と useTestCaseDetail フックをインポート
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

export default function TestStepDetailPage() {
  const params = useParams();
  const router = useRouter(); // useRouter を使用
  const projectId = params.id as string;
  const caseId = params.case_id as string;
  const stepId = params.step_id as string;

  const { testCase, isLoading: isLoadingCase, error: errorCase } = useTestCaseDetail(projectId, caseId);

  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false); // 削除確認ダイアログの表示状態
  const [isDeleting, setIsDeleting] = React.useState(false); // 削除処理中の状態


  // テストケース詳細から該当するテストステップを検索
  const testStep = React.useMemo(() => {
    if (!testCase?.steps) return null;
    return testCase.steps.find(step => step.id === stepId);
  }, [testCase, stepId]);

  // テストステップ削除処理
  const handleDeleteStep = async () => {
    setIsDeleting(true);
    try {
      await fetcher(`/api/projects/${projectId}/tests/${caseId}/steps/${stepId}`, 'DELETE');
      toast.success('テストステップが削除されました。');
      router.push(`/projects/${projectId}/tests/${caseId}`); // 削除成功後、テストケース詳細ページにリダイレクト
    } catch (error: any) {
      toast.error('テストステップの削除に失敗しました。', {
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

  if (!testCase || !testStep) {
    return (
      <div className="text-center py-8">
        <p>テストステップが見つかりません</p>
        <Button asChild className="mt-4">
          <Link href={`/projects/${projectId}/tests/${caseId}`}>テストケース詳細に戻る</Link>
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
    <> {/* Fragment で囲む */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 mb-4">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/projects/${projectId}/tests/${caseId}`}>
              <ArrowLeftIcon className="h-4 w-4 mr-1" />
              テストケース詳細に戻る
            </Link>
          </Button>
        </div>

        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">テストステップ: {testStep.sequence}</h1>
          {/* テストステップ編集・削除ボタン */}
          <div>
             <Button variant="outline" size="sm" className="mr-2" asChild> {/* asChild を追加 */}
               <Link href={`/projects/${projectId}/tests/${caseId}/steps/${stepId}/edit`}> {/* 編集ページへのリンク */}
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
            <CardTitle>テストステップ情報</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4">
              <div className="flex justify-between">
                <dt className="font-medium">ID</dt>
                <dd className="text-muted-foreground">{testStep.id}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">順序</dt>
                <dd className="text-muted-foreground">{testStep.sequence}</dd>
              </div>
               <div className="flex justify-between">
                <dt className="font-medium">メソッド</dt>
                <dd className="text-muted-foreground">{testStep.method}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">パス</dt>
                <dd className="text-muted-foreground">{testStep.path}</dd>
              </div>
               <div className="flex justify-between">
                <dt className="font-medium">期待するステータス</dt>
                <dd className="text-muted-foreground">{testStep.expected_status}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

         <Card>
          <CardHeader>
            <CardTitle>リクエスト/レスポンス情報</CardTitle>
          </CardHeader>
          <CardContent>
             <div className="grid gap-4">
               <div>
                 <h3 className="font-semibold mb-2">リクエストボディ</h3>
                 <div className="bg-muted p-4 rounded-md overflow-auto max-h-60">
                   <pre className="font-mono text-sm whitespace-pre-wrap">
                     {testStep.request_body ? formatJSON(testStep.request_body) : 'リクエストボディなし'}
                   </pre>
                 </div>
               </div>
               <div>
                 <h3 className="font-semibold mb-2">期待するレスポンスボディ</h3>
                  <div className="bg-muted p-4 rounded-md overflow-auto max-h-60">
                   <pre className="font-mono text-sm whitespace-pre-wrap">
                     {testStep.expected_response ? formatJSON(testStep.expected_response) : '期待するレスポンスボディなし'}
                   </pre>
                 </div>
               </div>
                {testStep.extracted_values && Object.keys(testStep.extracted_values).length > 0 && (
                  <div>
                    <h3 className="font-semibold mb-2">抽出された値</h3>
                     <div className="bg-muted p-4 rounded-md overflow-auto max-h-60">
                      <pre className="font-mono text-sm whitespace-pre-wrap">{formatJSON(testStep.extracted_values)}</pre>
                    </div>
                  </div>
                )}
             </div>
          </CardContent>
        </Card>
      </div>

      {/* 削除確認ダイアログ */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>テストステップを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は元に戻せません。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>キャンセル</AlertDialogCancel> {/* 削除中は無効化 */}
            <AlertDialogAction onClick={handleDeleteStep} disabled={isDeleting}> {/* 削除処理を実行 */}
              {isDeleting ? '削除中...' : '削除'} {/* 削除中の表示 */}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}