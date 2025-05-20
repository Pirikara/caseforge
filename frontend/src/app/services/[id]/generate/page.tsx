"use client"

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

export default function GeneratePageRedirect() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  
  useEffect(() => {
    router.replace(`/services/${serviceId}?tab=test-chains`);
  }, [serviceId, router]);
  
  return (
    <div className="flex items-center justify-center h-screen">
      <p className="text-muted-foreground">リダイレクト中...</p>
    </div>
  );
}
