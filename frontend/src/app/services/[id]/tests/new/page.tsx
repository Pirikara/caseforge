"use client"

import * as React from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
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

export default function NewTestCasePage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const serviceId = params.id as string;
  const suiteId = searchParams.get('suiteId');

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
  });

  const onSubmit = async (values: FormValues) => {
    try {
      const payload = {
        ...values,
        suite_id: suiteId,
        request_body: values.request_body ? JSON.parse(values.request_body) : null,
        expected_response: values.expected_response ? JSON.parse(values.expected_response) : null,
      };
      await fetcher(`/api/services/${serviceId}/tests`, 'POST', payload);
      toast.success('テストケースが作成されました。');
      if (suiteId) {
        router.push(`/services/${serviceId}/test-suites/${suiteId}`);
      } else {
        router.push(`/services/${serviceId}/tests`);
      }
    } catch (error: any) {
      toast.error('テストケースの作成に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={suiteId ? `/services/${serviceId}/test-suites/${suiteId}` : `/services/${serviceId}/tests`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            {suiteId ? 'テストスイート詳細に戻る' : 'テストケース一覧に戻る'}
          </Link>
        </Button>
      </div>

      <h1 className="text-3xl font-bold">新規テストケース作成</h1>

      <Card>
        <CardHeader>
          <CardTitle>テストケース情報入力</CardTitle>
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
              <Button type="submit">作成</Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
