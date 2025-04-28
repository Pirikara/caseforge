"use client"

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

export default function GeneratePageRedirect() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  
  useEffect(() => {
    // プロジェクト詳細ページのテストチェーン管理タブにリダイレクト
    router.replace(`/projects/${projectId}?tab=test-chains`);
  }, [projectId, router]);
  
  return (
    <div className="flex items-center justify-center h-screen">
      <p className="text-muted-foreground">リダイレクト中...</p>
    </div>
  );
}