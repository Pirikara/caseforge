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
import { useTestCaseDetail } from '@/hooks/useTestCases'; // テストケース詳細取得用フック

// フォームのスキーマ定義
const formSchema = z.object({
  title: z.string().min(1, { message: 'テストケース名は必須です。' }),
  method: z.string().min(1, { message: 'メソッドは必須です。' }),
  path: z.string().min(1, { message: 'パスは必須です。' }),
  expected_status: z.coerce.number().min(100, { message: '期待するステータスコードは必須です。' }), // 数値型に変換
  request_body: z.string().optional(),
  expected_response: z.string().optional(),
  purpose: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

export default function EditTestCasePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const caseId = params.case_id as string;

  const { testCase, isLoading, error } = useTestCaseDetail(projectId, caseId);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      title: '',
      method: '',
      path: '',
      expected_status: 200,
      request_body: '',
      expected_response: '',
      purpose: '',
    },
    values: { // testCase の値が取得できたらフォームにセット
      title: testCase?.title || '',
      method: testCase?.method || '',
      path: testCase?.path || '',
      expected_status: testCase?.expected_status || 200,
      request_body: testCase?.request_body ? JSON.stringify(testCase.request_body, null, 2) : '', // JSONを文字列に変換
      expected_response: testCase?.expected_response ? JSON.stringify(testCase.expected_response, null, 2) : '', // JSONを文字列に変換
      purpose: testCase?.purpose || '',
    },
  });

  // testCase がロードされた後にフォームの値をリセット
  React.useEffect(() => {
    if (testCase) {
      form.reset({
        title: testCase.title || '',
        method: testCase.method || '',
        path: testCase.path || '',
        expected_status: testCase.expected_status || 200,
        request_body: testCase.request_body ? JSON.stringify(testCase.request_body, null, 2) : '',
        expected_response: testCase.expected_response ? JSON.stringify(testCase.expected_response, null, 2) : '',
        purpose: testCase.purpose || '',
      });
    }
  }, [testCase, form]);


  const onSubmit = async (values: FormValues) => {
    try {
      // APIエンドポイントは仮
      const payload = {
        ...values,
        // request_body と expected_response は文字列として扱うか、JSONに変換するか検討
        request_body: values.request_body ? JSON.parse(values.request_body) : null,
        expected_response: values.expected_response ? JSON.parse(values.expected_response) : null,
      };
      await fetcher(`/api/projects/${projectId}/tests/${caseId}`, 'PUT', payload);
      toast.success('テストケースが更新されました。');
      router.push(`/projects/${projectId}/tests/${caseId}`);
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
          <Link href={`/projects/${projectId}/tests`}>テストケース一覧に戻る</Link>
        </Button>
      </div>
    );
  }


  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/projects/${projectId}/tests/${caseId}`}>
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
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>テストケース名</FormLabel>
                    <FormControl>
                      <Input placeholder="例: 正常系ユーザー登録" {...field} />
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
                      <Input placeholder="例: POST" {...field} />
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
                      <Input placeholder="例: /api/users" {...field} />
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
                      <Textarea placeholder='例: {"username": "testuser", "password": "password123"}' {...field} />
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
                      <Textarea placeholder='例: {"message": "User created successfully"}' {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
               <FormField
                control={form.control}
                name="purpose"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>目的 (任意)</FormLabel>
                    <FormControl>
                      <Textarea placeholder="このテストケースの目的" {...field} />
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