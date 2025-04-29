"use client"

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

export default function SchemaPageRedirect() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  
  useEffect(() => {
    // プロジェクト詳細ページのスキーマタブにリダイレクト
    router.replace(`/projects/${projectId}?tab=schema`);
  }, [projectId, router]);
  
  return (
    <div className="flex items-center justify-center h-screen">
      <p className="text-muted-foreground">リダイレクト中...</p>
    </div>
  );
}