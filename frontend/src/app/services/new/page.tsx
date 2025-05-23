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

const formSchema = z.object({
  service_id: z.string()
    .min(3, { message: 'サービスIDは3文字以上である必要があります' })
    .max(50, { message: 'サービスIDは50文字以下である必要があります' })
    .regex(/^[a-z0-9_-]+$/, { message: 'サービスIDは小文字、数字、ハイフン、アンダースコアのみ使用できます' }),
  name: z.string()
    .min(1, { message: 'サービス名は必須です' })
    .max(100, { message: 'サービス名は100文字以下である必要があります' }),
  description: z.string().max(500, { message: '説明は500文字以下である必要があります' }).optional(),
});

export default function NewServicePage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      service_id: '',
      name: '',
      description: '',
    },
  });
  
  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      setIsSubmitting(true);
      
      const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
      const response = await fetch(`${API}/api/services/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          service_id: values.service_id,
          name: values.name,
          description: values.description || '',
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'サービスの作成に失敗しました');
      }
      
      const data = await response.json();
      
      toast.success('サービスが作成されました', {
        description: `サービス「${values.name}」が正常に作成されました。`,
      });
      
      router.push(`/services/${values.service_id}`);
    } catch (error) {
      console.error('サービス作成エラー:', error);
      toast.error('エラーが発生しました', {
        description: error instanceof Error ? error.message : '不明なエラーが発生しました',
      });
    } finally {
      setIsSubmitting(false);
    }
  }
  
  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">新規サービス作成</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>サービス情報</CardTitle>
          <CardDescription>
            新しいサービスの基本情報を入力してください。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="service_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>サービスID</FormLabel>
                    <FormControl>
                      <Input placeholder="my-service" {...field} />
                    </FormControl>
                    <FormDescription>
                      サービスを識別するための一意のIDです。小文字、数字、ハイフン、アンダースコアのみ使用できます。
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
                    <FormLabel>サービス名</FormLabel>
                    <FormControl>
                      <Input placeholder="マイサービス" {...field} />
                    </FormControl>
                    <FormDescription>
                      サービスの表示名です。
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
                        placeholder="サービスの説明を入力してください"
                        className="resize-none"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      サービスの詳細な説明です。
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => router.push('/services')}
                  disabled={isSubmitting}
                >
                  キャンセル
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? '作成中...' : 'サービスを作成'}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
