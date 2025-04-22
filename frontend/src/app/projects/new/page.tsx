"use client"

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';

// フォームのバリデーションスキーマ
const formSchema = z.object({
  project_id: z.string()
    .min(3, { message: 'プロジェクトIDは3文字以上である必要があります' })
    .max(50, { message: 'プロジェクトIDは50文字以下である必要があります' })
    .regex(/^[a-z0-9_-]+$/, { message: 'プロジェクトIDは小文字、数字、ハイフン、アンダースコアのみ使用できます' }),
  name: z.string()
    .min(1, { message: 'プロジェクト名は必須です' })
    .max(100, { message: 'プロジェクト名は100文字以下である必要があります' }),
  description: z.string().max(500, { message: '説明は500文字以下である必要があります' }).optional(),
});

export default function NewProjectPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  
  // フォームの初期化
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      project_id: '',
      name: '',
      description: '',
    },
  });
  
  // フォーム送信処理
  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      setIsSubmitting(true);
      
      const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
      const response = await fetch(`${API}/api/projects/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: values.project_id,
          name: values.name,
          description: values.description || '',
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'プロジェクトの作成に失敗しました');
      }
      
      const data = await response.json();
      
      toast.success('プロジェクトが作成されました', {
        description: `プロジェクト「${values.name}」が正常に作成されました。`,
      });
      
      // プロジェクト詳細ページにリダイレクト
      router.push(`/projects/${values.project_id}`);
    } catch (error) {
      console.error('プロジェクト作成エラー:', error);
      toast.error('エラーが発生しました', {
        description: error instanceof Error ? error.message : '不明なエラーが発生しました',
      });
    } finally {
      setIsSubmitting(false);
    }
  }
  
  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">新規プロジェクト作成</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>プロジェクト情報</CardTitle>
          <CardDescription>
            新しいプロジェクトの基本情報を入力してください。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="project_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>プロジェクトID</FormLabel>
                    <FormControl>
                      <Input placeholder="my-project" {...field} />
                    </FormControl>
                    <FormDescription>
                      プロジェクトを識別するための一意のIDです。小文字、数字、ハイフン、アンダースコアのみ使用できます。
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>プロジェクト名</FormLabel>
                    <FormControl>
                      <Input placeholder="マイプロジェクト" {...field} />
                    </FormControl>
                    <FormDescription>
                      プロジェクトの表示名です。
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>説明（オプション）</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="プロジェクトの説明を入力してください"
                        className="resize-none"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      プロジェクトの詳細な説明です。
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => router.push('/projects')}
                  disabled={isSubmitting}
                >
                  キャンセル
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? '作成中...' : 'プロジェクトを作成'}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}