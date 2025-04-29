"use client"

import { useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';

export default function RunPageRedirect() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = params.id as string;
  const chainId = searchParams.get('chain_id');
  
  useEffect(() => {
    // プロジェクト詳細ページのテスト実行タブにリダイレクト
    // chain_idパラメータがある場合は、それも引き継ぐ
    const url = chainId 
      ? `/projects/${projectId}?tab=test-execution&chain_id=${chainId}`
      : `/projects/${projectId}?tab=test-execution`;
    
    router.replace(url);
  }, [projectId, chainId, router]);
  
  return (
    <div className="flex items-center justify-center h-screen">
      <p className="text-muted-foreground">リダイレクト中...</p>
    </div>
  );
}