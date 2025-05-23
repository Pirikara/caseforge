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
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { PlusIcon, TrashIcon, ArrowUpIcon, ArrowDownIcon, EditIcon } from 'lucide-react';
import { TestCaseDetail, TestStep } from '@/hooks/useTestCases';
import Link from 'next/link';
import { toast } from 'sonner';
import { fetcher } from '@/utils/fetcher';

// フォームのスキーマ定義
const formSchema = z.object({
  title: z.string().min(1, { message: 'テストケース名は必須です。' }),
  method: z.string().min(1, { message: 'メソッドは必須です。' }),
  path: z.string().min(1, { message: 'パスは必須です。' }),
  expected_status: z.coerce.number().min(100, { message: '期待するステータスコードは必須です。' }),
  request_body: z.string().optional(),
  expected_response: z.string().optional(),
  purpose: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

interface TestCaseFormProps {
  testCase: TestCaseDetail;
  onSave: (data: any) => Promise<void>;
  serviceId: string;
}

export function TestCaseForm({ testCase, onSave, serviceId }: TestCaseFormProps) {
  const [steps, setSteps] = React.useState<TestStep[]>(testCase.steps || []);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      title: testCase.title || '',
      method: testCase.method || '',
      path: testCase.path || '',
      expected_status: testCase.expected_status || 200,
      request_body: testCase.request_body ? JSON.stringify(testCase.request_body, null, 2) : '',
      expected_response: testCase.expected_response ? JSON.stringify(testCase.expected_response, null, 2) : '',
      purpose: testCase.purpose || '',
    },
  });

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
      setSteps(testCase.steps || []);
    }
  }, [testCase, form]);

  const handleSubmit = async (values: FormValues) => {
    setIsSubmitting(true);
    try {
      const formData = {
        ...values,
        request_body: values.request_body ? JSON.parse(values.request_body) : null,
        expected_response: values.expected_response ? JSON.parse(values.expected_response) : null,
        steps: steps
      };
      
      await onSave(formData);
    } catch (error: any) {
      if (error.message.includes('JSON')) {
        toast.error('JSONの形式が正しくありません。', {
          description: error.message,
        });
      } else {
        toast.error('エラーが発生しました。', {
          description: error.message,
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteStep = async (stepId: string) => {
    try {
      await fetcher(`/api/services/${serviceId}/test-cases/${testCase.id}/steps/${stepId}`, 'DELETE');
      setSteps(steps.filter(step => step.id !== stepId));
      toast.success('テストステップが削除されました。');
    } catch (error: any) {
      toast.error('テストステップの削除に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    }
  };

  // テストステップの順序を上げる
  const handleMoveStepUp = async (index: number) => {
    if (index <= 0) return;
    
    try {
      const newSteps = [...steps];
      const temp = newSteps[index].sequence;
      newSteps[index].sequence = newSteps[index - 1].sequence;
      newSteps[index - 1].sequence = temp;
      
      newSteps.sort((a, b) => a.sequence - b.sequence);
      
      await Promise.all([
        fetcher(`/api/services/${serviceId}/test-cases/${testCase.id}/steps/${newSteps[index].id}`, 'PUT', {
          sequence: newSteps[index].sequence
        }),
        fetcher(`/api/services/${serviceId}/test-cases/${testCase.id}/steps/${newSteps[index - 1].id}`, 'PUT', {
          sequence: newSteps[index - 1].sequence
        })
      ]);
      
      setSteps(newSteps);
      toast.success('テストステップの順序が更新されました。');
    } catch (error: any) {
      toast.error('テストステップの順序更新に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    }
  };

  const handleMoveStepDown = async (index: number) => {
    if (index >= steps.length - 1) return;
    
    try {
      const newSteps = [...steps];
      // 順序を入れ替え
      const temp = newSteps[index].sequence;
      newSteps[index].sequence = newSteps[index + 1].sequence;
      newSteps[index + 1].sequence = temp;
      
      // 順序でソート
      newSteps.sort((a, b) => a.sequence - b.sequence);
      
      // APIを呼び出して順序を更新
      await Promise.all([
        fetcher(`/api/services/${serviceId}/test-cases/${testCase.id}/steps/${newSteps[index].id}`, 'PUT', {
          sequence: newSteps[index].sequence
        }),
        fetcher(`/api/services/${serviceId}/test-cases/${testCase.id}/steps/${newSteps[index + 1].id}`, 'PUT', {
          sequence: newSteps[index + 1].sequence
        })
      ]);
      
      // API呼び出しが成功した場合のみ状態を更新
      setSteps(newSteps);
      toast.success('テストステップの順序が更新されました。');
    } catch (error: any) {
      toast.error('テストステップの順序更新に失敗しました。', {
        description: error.message || '不明なエラーが発生しました。',
      });
    }
  };

  return (
    <div className="space-y-6">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
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

          <div className="space-y-4 pt-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium">テストステップ</h3>
              <Button asChild variant="outline" size="sm">
                <Link href={`/projects/${serviceId}/tests/${testCase.id}/steps/new`}>
                  <PlusIcon className="h-4 w-4 mr-1" />
                  新規ステップ追加
                </Link>
              </Button>
            </div>

            <Card>
              <CardContent className="p-0">
                {steps.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[80px]">順序</TableHead>
                        <TableHead className="w-[80px]">メソッド</TableHead>
                        <TableHead>パス</TableHead>
                        <TableHead className="w-[120px]">期待するステータス</TableHead>
                        <TableHead className="w-[180px]">アクション</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {steps.map((step, index) => (
                        <TableRow key={step.id}>
                          <TableCell>{step.sequence}</TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              step.method === 'GET' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200' :
                              step.method === 'POST' ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200' :
                              step.method === 'PUT' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200' :
                              step.method === 'DELETE' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200' :
                              'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200'
                            }`}>
                              {step.method}
                            </span>
                          </TableCell>
                          <TableCell className="font-mono text-sm">{step.path}</TableCell>
                          <TableCell>{step.expected_status}</TableCell>
                          <TableCell>
                            <div className="flex space-x-1">
                              <Button variant="outline" size="icon" onClick={() => handleMoveStepUp(index)} disabled={index === 0}>
                                <ArrowUpIcon className="h-4 w-4" />
                              </Button>
                              <Button variant="outline" size="icon" onClick={() => handleMoveStepDown(index)} disabled={index === steps.length - 1}>
                                  <ArrowDownIcon className="h-4 w-4" />
                              </Button>
                              <Button variant="outline" size="icon" asChild>
                                <Link href={`/projects/${serviceId}/tests/${testCase.id}/steps/${step.id}/edit`}>
                                  <EditIcon className="h-4 w-4" />
                                </Link>
                              </Button>
                              <Button variant="outline" size="icon" onClick={() => handleDeleteStep(step.id)}>
                                <TrashIcon className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-muted-foreground">このテストケースにはまだテストステップがありません。</p>
                    <Button asChild className="mt-4" variant="outline">
                      <Link href={`/projects/${serviceId}/tests/${testCase.id}/steps/new`}>
                        <PlusIcon className="h-4 w-4 mr-1" />
                        新規ステップ追加
                      </Link>
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

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
