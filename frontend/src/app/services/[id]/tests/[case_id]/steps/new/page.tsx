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

export default function NewTestStepPage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  const caseId = params.case_id as string;

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
  });

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
      await fetcher(`/api/services/${serviceId}/tests/${caseId}/steps`, 'POST', payload);
      toast.success('テストステップが作成されました。');
      router.push(`/services/${serviceId}/tests/${caseId}`); // テストケース詳細ページに戻る
    } catch (error: any) {
      toast.error('テストステップの作成に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/services/${serviceId}/tests/${caseId}`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            テストケース詳細に戻る
          </Link>
        </Button>
      </div>

      <h1 className="text-3xl font-bold">新規テストステップ作成</h1>

      <Card>
        <CardHeader>
          <CardTitle>テストステップ情報入力</CardTitle>
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
                      <Input type="number" placeholder="例: 1" {...field} onChange={e => field.onChange(e.target.valueAsNumber)} />
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
                      <Input type="number" placeholder="例: 200" {...field} onChange={e => field.onChange(e.target.valueAsNumber)} /> 
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
              <Button type="submit">作成</Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
