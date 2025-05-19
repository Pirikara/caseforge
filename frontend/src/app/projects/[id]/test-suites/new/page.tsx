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
  name: z.string().min(1, { message: 'テストスイート名は必須です。' }),
  target_method: z.string().min(1, { message: '対象メソッドは必須です。' }),
  target_path: z.string().min(1, { message: '対象パスは必須です。' }),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

export default function NewTestSuitePage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      target_method: '',
      target_path: '',
      description: '',
    },
  });

  const onSubmit = async (values: FormValues) => {
    try {
      // APIエンドポイントは仮
      await fetcher(`/api/services/${serviceId}/test-suites`, 'POST', values);
      toast.success('テストスイートが作成されました。');
      router.push(`/services/${serviceId}/test-suites`);
    } catch (error: any) {
      toast.error('テストスイートの作成に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/services/${serviceId}/test-suites`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            テストスイート一覧に戻る
          </Link>
        </Button>
      </div>

      <h1 className="text-3xl font-bold">新規テストスイート作成</h1>

      <Card>
        <CardHeader>
          <CardTitle>テストスイート情報入力</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>テストスイート名</FormLabel>
                    <FormControl>
                      <Input placeholder="例: ユーザー登録テスト" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="target_method"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>対象メソッド</FormLabel>
                    <FormControl>
                      <Input placeholder="例: POST" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="target_path"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>対象パス</FormLabel>
                    <FormControl>
                      <Input placeholder="例: /api/users" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
               <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>説明 (任意)</FormLabel>
                    <FormControl>
                      <Textarea placeholder="テストスイートの説明" {...field} />
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
