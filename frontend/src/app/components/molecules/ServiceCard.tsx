"use client"

import * as React from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PlayIcon, FileTextIcon } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';

interface Service {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface ServiceCardProps {
  service: Service;
}

export function ServiceCard({ service }: ServiceCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <CardTitle className="text-xl">
          <Link href={`/services/${service.id}`} className="hover:underline">
            {service.name}
          </Link>
        </CardTitle>
        <CardDescription>
          {service.description || 'サービスの説明はありません'}
        </CardDescription>
      </CardHeader>
      <CardContent className="pb-2">
        <div className="text-sm text-muted-foreground">
          作成日: {formatDistanceToNow(new Date(service.created_at), { addSuffix: true, locale: ja })}
        </div>
      </CardContent>
      <CardFooter className="flex justify-between">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/services/${service.id}/run`}>
            <PlayIcon className="h-4 w-4 mr-1" />
            テスト実行
          </Link>
        </Button>
        <Button variant="outline" size="sm" asChild>
          <Link href={`/services/${service.id}`}>
            <FileTextIcon className="h-4 w-4 mr-1" />
            詳細
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
