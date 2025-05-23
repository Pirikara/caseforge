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
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { FileUpload } from '@/components/molecules/FileUpload';
import { useServices } from '@/hooks/useServices';
import { toast } from 'sonner';

// フォームのバリデーションスキーマ
const formSchema = z.object({
  service_id: z.string().min(1, { message: 'サービスIDは必須です' }),
  file: z.instanceof(File, { message: 'ファイルは必須です' }),
});

export default function UploadPage() {
  const router = useRouter();
  const { services, isLoading: isLoadingServices } = useServices();
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      service_id: '',
    },
  });

  const handleFileSelect = (file: File) => {
    form.setValue('file', file, { shouldValidate: true });
  };
  
  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      setIsSubmitting(true);
      
      const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
      
      const formData = new FormData();
      formData.append('file', values.file);
      
      const response = await fetch(`${API}/api/services/${values.service_id}/schema`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'スキーマのアップロードに失敗しました');
      }
      
      toast.success('スキーマがアップロードされました', {
        description: `サービス「${values.service_id}」にスキーマがアップロードされました。`,
      });
      
      router.push(`/services/${values.service_id}`);
    } catch (error) {
      console.error('スキーマアップロードエラー:', error);
      toast.error('エラーが発生しました', {
        description: error instanceof Error ? error.message : '不明なエラーが発生しました',
      });
    } finally {
      setIsSubmitting(false);
    }
  }
  
  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">OpenAPIスキーマのアップロード</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>スキーマファイル</CardTitle>
          <CardDescription>
            OpenAPIスキーマファイル（YAML/JSON）をアップロードしてください。
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
                      スキーマをアップロードするサービスのIDを入力してください。
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="file"
                render={() => (
                  <FormItem>
                    <FormLabel>スキーマファイル</FormLabel>
                    <FormControl>
                      <FileUpload
                        accept=".yaml,.yml,.json"
                        maxSize={10}
                        onFileSelect={handleFileSelect}
                      />
                    </FormControl>
                    <FormDescription>
                      OpenAPIスキーマファイル（YAML/JSON）をアップロードしてください。最大10MB。
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
                  {isSubmitting ? 'アップロード中...' : 'アップロード'}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
