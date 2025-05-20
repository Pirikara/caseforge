"use client"

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeftIcon } from 'lucide-react';
import { toast } from 'sonner';
import { fetcher } from '@/utils/fetcher';
import { useTestCaseDetail, TestStep } from '@/hooks/useTestCases';
import { TestCaseForm } from './TestCaseForm';

export default function EditTestCasePage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  const caseId = params.case_id as string;

  const { testCase, isLoading, error, mutate } = useTestCaseDetail(serviceId, caseId);

  const handleSave = async (formData: any) => {
    try {
      // APIエンドポイントにデータを送信
      await fetcher(`/api/services/${serviceId}/test-cases/${caseId}`, 'PUT', formData);
      toast.success('テストケースが更新されました。');
      mutate(); // データを再取得
      router.push(`/projects/${serviceId}/tests/${caseId}`);
    } catch (error: any) {
      toast.error('テストケースの更新に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    }
  };

  if (isLoading) {
    return <div className="text-center py-8">読み込み中...</div>;
  }

  if (error) {
    return <div className="text-center py-8 text-red-500">テストケースの読み込み中にエラーが発生しました: {error.message}</div>;
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
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/projects/${serviceId}/tests/${caseId}`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            テストケース詳細に戻る
          </Link>
        </Button>
      </div>

      <h1 className="text-3xl font-bold">テストケース編集: {testCase.title || '名前なし'}</h1>

      <Card>
        <CardHeader>
          <CardTitle>テストケース情報編集</CardTitle>
        </CardHeader>
        <CardContent>
          <TestCaseForm 
            testCase={testCase} 
            onSave={handleSave} 
            serviceId={serviceId}
          />
        </CardContent>
      </Card>
    </div>
  );
}
