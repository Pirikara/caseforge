"use client"

import * as React from 'react';
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
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TestStepDetail } from '@/hooks/useTestSteps';
import { RequestBodyEditor } from './components/RequestBodyEditor';
import { ResponseValidator } from './components/ResponseValidator';
import { PathParamEditor } from './components/PathParamEditor';
import { QueryParamEditor } from './components/QueryParamEditor';
import { HeaderEditor } from './components/HeaderEditor';
import { ExtractorEditor } from './components/ExtractorEditor';

// フォームのスキーマ定義
const formSchema = z.object({
  name: z.string().optional(),
  method: z.string().min(1, { message: 'メソッドは必須です。' }),
  path: z.string().min(1, { message: 'パスは必須です。' }),
  expected_status: z.coerce.number().min(100, { message: '期待するステータスコードは必須です。' }),
  request_body: z.any().optional(),
  expected_response: z.any().optional(),
  request_headers: z.record(z.string()).optional(),
  path_params: z.record(z.string()).optional(),
  query_params: z.record(z.string()).optional(),
  extract_rules: z.record(z.string()).optional(),
});

type FormValues = z.infer<typeof formSchema>;

interface TestStepFormProps {
  testStep: TestStepDetail;
  onSave: (data: any) => Promise<void>;
  serviceId: string;
  caseId: string;
}

export function TestStepForm({ testStep, onSave, serviceId, caseId }: TestStepFormProps) {
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: testStep.name || '',
      method: testStep.method || '',
      path: testStep.path || '',
      expected_status: testStep.expected_status || 200,
      request_body: testStep.request_body || null,
      expected_response: testStep.expected_response || null,
      request_headers: testStep.request_headers || {},
      path_params: testStep.path_params || {},
      query_params: testStep.query_params || {},
      extract_rules: testStep.extract_rules || {},
    },
  });

  // testStep が更新されたらフォームの値をリセット
  React.useEffect(() => {
    if (testStep) {
      form.reset({
        name: testStep.name || '',
        method: testStep.method || '',
        path: testStep.path || '',
        expected_status: testStep.expected_status || 200,
        request_body: testStep.request_body || null,
        expected_response: testStep.expected_response || null,
        request_headers: testStep.request_headers || {},
        path_params: testStep.path_params || {},
        query_params: testStep.query_params || {},
        extract_rules: testStep.extract_rules || {},
      });
    }
  }, [testStep, form]);

  const handleSubmit = async (values: FormValues) => {
    setIsSubmitting(true);
    try {
      // フォームデータを整形
      const formData = {
        ...values,
      };
      
      await onSave(formData);
    } catch (error: any) {
      console.error('Error submitting form:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>ステップ名 (任意)</FormLabel>
                  <FormControl>
                    <Input placeholder="例: ユーザー情報取得" {...field} />
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
          </div>

          <FormField
            control={form.control}
            name="path"
            render={({ field }) => (
              <FormItem>
                <FormLabel>パス</FormLabel>
                <FormControl>
                  <Input placeholder="例: /api/users/{id}" {...field} />
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

          <Tabs defaultValue="request-body" className="w-full">
            <TabsList className="grid grid-cols-3 md:grid-cols-6">
              <TabsTrigger value="request-body">リクエストボディ</TabsTrigger>
              <TabsTrigger value="response">レスポンス検証</TabsTrigger>
              <TabsTrigger value="path-params">パスパラメータ</TabsTrigger>
              <TabsTrigger value="query-params">クエリパラメータ</TabsTrigger>
              <TabsTrigger value="headers">ヘッダー</TabsTrigger>
              <TabsTrigger value="extractors">変数抽出</TabsTrigger>
            </TabsList>
            <TabsContent value="request-body">
              <RequestBodyEditor
                control={form.control}
                name="request_body"
              />
            </TabsContent>
            <TabsContent value="response">
              <ResponseValidator
                control={form.control}
                name="expected_response"
              />
            </TabsContent>
            <TabsContent value="path-params">
              <PathParamEditor
                control={form.control}
                name="path_params"
              />
            </TabsContent>
            <TabsContent value="query-params">
              <QueryParamEditor
                control={form.control}
                name="query_params"
              />
            </TabsContent>
            <TabsContent value="headers">
              <HeaderEditor
                control={form.control}
                name="request_headers"
              />
            </TabsContent>
            <TabsContent value="extractors">
              <ExtractorEditor
                control={form.control}
                name="extract_rules"
              />
            </TabsContent>
          </Tabs>

          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? '保存中...' : '保存'}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
