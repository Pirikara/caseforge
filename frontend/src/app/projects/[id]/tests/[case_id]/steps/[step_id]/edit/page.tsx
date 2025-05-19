"use client"

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ArrowLeftIcon } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { toast } from 'sonner';
import { fetcher } from '@/utils/fetcher';
import { useTestCaseDetail, TestStep } from '@/hooks/useTestCases'; // TestStep 型と useTestCaseDetail フックをインポート

// フォームのスキーマ定義
const formSchema = z.object({
  sequence: z.coerce.number().min(0, { message: '順序は必須です。0以上の数値を入力してください。' }), // 数値型に変換
  method: z.string().min(1, { message: 'メソッドは必須です。' }),
  path: z.string().min(1, { message: 'パスは必須です。' }),
  expected_status: z.coerce.number().min(100, { message: '期待するステータスコードは必須です。' }), // 数値型に変換
  request_body: z.string().optional(),
  expected_response: z.string().optional(),
  extracted_values: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

export default function EditTestStepPage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  const caseId = params.case_id as string;
  const stepId = params.step_id as string;

  const { testCase, isLoading: isLoadingCase, error: errorCase } = useTestCaseDetail(serviceId, caseId);

  // テストケース詳細から該当するテストステップを検索
  const testStep = React.useMemo(() => {
    if (!testCase?.steps) return null;
    return testCase.steps.find(step => step.id === stepId);
  }, [testCase, stepId]);


  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      sequence: 0,
      method: '',
      path: '',
      expected_status: 200,
      request_body: '',
      expected_response: '',
      extracted_values: '',
    },
    values: { // testStep の値が取得できたらフォームにセット
      sequence: testStep?.sequence || 0,
      method: testStep?.method || '',
      path: testStep?.path || '',
      expected_status: testStep?.expected_status || 200,
      request_body: testStep?.request_body ? JSON.stringify(testStep.request_body, null, 2) : '', // JSONを文字列に変換
      expected_response: testStep?.expected_response ? JSON.stringify(testStep.expected_response, null, 2) : '', // JSONを文字列に変換
      extracted_values: testStep?.extracted_values ? JSON.stringify(testStep.extracted_values, null, 2) : '', // JSONを文字列に変換
    },
  });

  // testStep がロードされた後にフォームの値をリセット
  React.useEffect(() => {
    if (testStep) {
      form.reset({
        sequence: testStep.sequence || 0,
        method: testStep.method || '',
        path: testStep.path || '',
        expected_status: testStep.expected_status || 200,
        request_body: testStep.request_body ? JSON.stringify(testStep.request_body, null, 2) : '',
        expected_response: testStep.expected_response ? JSON.stringify(testStep.expected_response, null, 2) : '',
        extracted_values: testStep.extracted_values ? JSON.stringify(testStep.extracted_values, null, 2) : '',
      });
    }
  }, [testStep, form]);


  const onSubmit = async (values: FormValues) => {
    try {
      // APIエンドポイントは仮
      const payload = {
        ...values,
        // request_body, expected_response, extracted_values は文字列として扱うか、JSONに変換するか検討
        request_body: values.request_body ? JSON.parse(values.request_body) : null,
        expected_response: values.expected_response ? JSON.parse(values.expected_response) : null,
        extracted_values: values.extracted_values ? JSON.parse(values.extracted_values) : null,
      };
      await fetcher(`/api/services/${serviceId}/tests/${caseId}/steps/${stepId}`, 'PUT', payload);
      toast.success('テストステップが更新されました。');
      router.push(`/services/${serviceId}/tests/${caseId}/steps/${stepId}`); // テストステップ詳細ページに戻る
    } catch (error: any) {
      toast.error('テストステップの更新に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
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
          <Link href={`/services/${serviceId}/tests/${caseId}`}>テストケース詳細に戻る</Link>
        </Button>
      </div>
    );
  }


  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/services/${serviceId}/tests/${caseId}/steps/${stepId}`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            テストステップ詳細に戻る
          </Link>
        </Button>
      </div>

      <h1 className="text-3xl font-bold">テストステップ編集: {testStep.sequence}</h1>

      <Card>
        <CardHeader>
          <CardTitle>テストステップ情報編集</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
               <FormField
                control={form.control}
                name="sequence"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>順序</FormLabel>
                    <FormControl>
                      <Input type="number" placeholder="例: 1" {...field} onChange={e => field.onChange(e.target.valueAsNumber)} /> {/* 数値として扱う */}
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="method"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>メソッド</FormLabel>
                    <FormControl>
                      <Input placeholder="例: GET" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="path"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>パス</FormLabel>
                    <FormControl>
                      <Input placeholder="例: /api/users/1" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
               <FormField
                control={form.control}
                name="expected_status"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>期待するステータスコード</FormLabel>
                    <FormControl>
                      <Input type="number" placeholder="例: 200" {...field} onChange={e => field.onChange(e.target.valueAsNumber)} /> {/* 数値として扱う */}
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
               <FormField
                control={form.control}
                name="request_body"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>リクエストボディ (JSON, 任意)</FormLabel>
                    <FormControl>
                      <Textarea placeholder='例: {"key": "value"}' {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
               <FormField
                control={form.control}
                name="expected_response"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>期待するレスポンスボディ (JSON, 任意)</FormLabel>
                    <FormControl>
                      <Textarea placeholder='例: {"result": "success"}' {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
               <FormField
                control={form.control}
                name="extracted_values"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>抽出する値 (JSONPath, 任意)</FormLabel>
                    <FormControl>
                      <Textarea placeholder='例: {"user_id": "$.id"}' {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit">更新</Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
