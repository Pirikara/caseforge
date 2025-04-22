"use client"

import * as React from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PlusIcon, UploadIcon, PlayIcon, FileTextIcon } from 'lucide-react';

export function QuickActions() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>クイックアクション</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        <Button asChild className="w-full">
          <Link href="/projects/new">
            <PlusIcon className="h-4 w-4 mr-2" />
            新規プロジェクト作成
          </Link>
        </Button>
        <Button asChild variant="outline" className="w-full">
          <Link href="/upload">
            <UploadIcon className="h-4 w-4 mr-2" />
            スキーマアップロード
          </Link>
        </Button>
        <Button asChild variant="secondary" className="w-full">
          <Link href="/projects">
            <FileTextIcon className="h-4 w-4 mr-2" />
            プロジェクト一覧
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}