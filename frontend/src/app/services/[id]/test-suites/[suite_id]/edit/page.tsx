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
import { useTestSuiteDetail } from '@/hooks/useTestChains';

const formSchema = z.object({
  name: z.string().min(1, { message: 'テストスイート名は必須です。' }),
  target_method: z.string().min(1, { message: '対象メソッドは必須です。' }),
  target_path: z.string().min(1, { message: '対象パスは必須です。' }),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

export default function EditTestSuitePage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  const suiteId = params.suite_id as string;

  const { testSuite, isLoading, error } = useTestSuiteDetail(serviceId, suiteId);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: testSuite?.name || '',
      target_method: testSuite?.target_method || '',
      target_path: testSuite?.target_path || '',
      description: testSuite?.description || '',
    },
    values: {
      name: testSuite?.name || '',
      target_method: testSuite?.target_method || '',
      target_path: testSuite?.target_path || '',
      description: testSuite?.description || '',
    },
    // resetOptions: { // testSuite が更新されたらフォームをリセット
    //   keepDirtyValues: true, // ユーザーが入力した値は保持
    // },
  });

  React.useEffect(() => {
    if (testSuite) {
      form.reset({
        name: testSuite.name || '',
        target_method: testSuite.target_method || '',
        target_path: testSuite.target_path || '',
        description: testSuite.description || '',
      });
    }
  }, [testSuite, form]);


  const onSubmit = async (values: FormValues) => {
    try {
      await fetcher(`/api/services/${serviceId}/test-suites/${suiteId}`, 'PUT', values);
      toast.success('テストスイートが更新されました。');
      router.push(`/services/${serviceId}/test-suites/${suiteId}`);
    } catch (error: any) {
      toast.error('テストスイートの更新に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    }
  };

  if (isLoading) {
    return <div className="text-center py-8">読み込み中...</div>;
  }

  if (error) {
    return <div className="text-center py-8 text-red-500">テストスイートの読み込み中にエラーが発生しました: {error.message}</div>;
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
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/services/${serviceId}/test-suites/${suiteId}`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            テストスイート詳細に戻る
          </Link>
        </Button>
      </div>

      <h1 className="text-3xl font-bold">テストスイート編集: {testSuite.name}</h1>

      <Card>
        <CardHeader>
          <CardTitle>テストスイート情報編集</CardTitle>
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
              <Button type="submit">更新</Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
