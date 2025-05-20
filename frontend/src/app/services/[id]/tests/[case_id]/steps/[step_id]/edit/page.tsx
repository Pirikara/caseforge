"use client"

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeftIcon } from 'lucide-react';
import { toast } from 'sonner';
import { useTestStepDetail, updateTestStep } from '@/hooks/useTestSteps';
import { TestStepForm } from './TestStepForm';

export default function EditTestStepPage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  const caseId = params.case_id as string;
  const stepId = params.step_id as string;

:start_line:20
-------
  const { testStep, isLoading, error, mutate } = useTestStepDetail(serviceId, caseId, stepId);

  const handleSave = async (formData: any) => {
    try {
      // APIエンドポイントにデータを送信
:start_line:25
-------
      await updateTestStep(serviceId, caseId, stepId, formData);
      toast.success('テストステップが更新されました。');
      mutate(); // データを再取得
      router.push(`/projects/${serviceId}/tests/${caseId}`);
    } catch (error: any) {
      toast.error('テストステップの更新に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    }
  };

  if (isLoading) {
    return <div className="text-center py-8">読み込み中...</div>;
  }

  if (error) {
    return <div className="text-center py-8 text-red-500">テストステップの読み込み中にエラーが発生しました: {error.message}</div>;
  }

  if (!testStep) {
    return (
      <div className="text-center py-8">
        <p>テストステップが見つかりません</p>
        <Button asChild className="mt-4">
          <Link href={`/projects/${serviceId}/tests/${caseId}`}>テストケース詳細に戻る</Link>
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

      <h1 className="text-3xl font-bold">テストステップ編集: {testStep.name || `ステップ ${testStep.sequence}`}</h1>

      <Card>
        <CardHeader>
          <CardTitle>テストステップ情報編集</CardTitle>
        </CardHeader>
        <CardContent>
          <TestStepForm 
            testStep={testStep} 
            onSave={handleSave} 
            serviceId={serviceId}
            caseId={caseId}
          />
        </CardContent>
      </Card>
    </div>
  );
}
