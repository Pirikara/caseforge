"use client"

import * as React from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ArrowLeftIcon } from 'lucide-react';
import { useTestSuites } from '@/hooks/useTestChains'

export default function TestSuitesPage() {
  const params = useParams();
  const serviceId = params.id as string;

  const { testSuites, isLoading, error } = useTestSuites(serviceId);

  if (isLoading) {
    return <div className="text-center py-8">読み込み中...</div>;
  }

  if (error) {
    return <div className="text-center py-8 text-red-500">エラーが発生しました: {error.message}</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/services/${serviceId}`}>
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            サービス詳細に戻る
          </Link>
        </Button>
      </div>

      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">テストスイート一覧</h1>
        {/* 新規テストスイート作成ボタン（後で実装） */}
        <Button asChild>
          <Link href={`/services/${serviceId}/test-suites/new`}>
            新規テストスイート作成
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>テストスイート</CardTitle>
        </CardHeader>
        <CardContent>
          {testSuites && testSuites.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名前</TableHead>
                  <TableHead>対象メソッド</TableHead>
                  <TableHead>対象パス</TableHead>
                  <TableHead>テストケース数</TableHead>
                  <TableHead className="w-[100px]">アクション</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {testSuites.map((suite) => (
                  <TableRow key={suite.id}>
                    <TableCell className="font-medium">{suite.name}</TableCell>
                    <TableCell>{suite.target_method}</TableCell>
                    <TableCell>{suite.target_path}</TableCell>
                    <TableCell>{suite.test_cases?.length || 0}</TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/services/${serviceId}/test-suites/${suite.id}`}>
                          詳細
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8">
              <p className="text-muted-foreground">テストスイートはまだありません。</p>
              {/* 新規テストスイート作成ボタン（後で実装） */}
              <Button asChild className="mt-4">
                <Link href={`/services/${serviceId}/test-suites/new`}>
                  新規テストスイート作成
                </Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
