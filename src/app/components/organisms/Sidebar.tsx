"use client"

import * as React from 'react';
import Link from 'next/link';
import { PlusIcon } from 'lucide-react';
import { Button } from '../ui/button';
import { useProjects } from '@/app/hooks/useProjects';

export function Sidebar() {
  const { projects, isLoading, error } = useProjects();
  
  return (
    <aside className="w-64 border-r border-border bg-background p-4 hidden md:block">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">プロジェクト</h2>
        <Button size="sm" asChild>
          <Link href="/projects/new">
            <PlusIcon className="h-4 w-4 mr-1" />
            新規
          </Link>
        </Button>
      </div>
      
      {isLoading ? (
        <div>読み込み中...</div>
      ) : error ? (
        <div>エラーが発生しました</div>
      ) : (
        <ul className="space-y-1">
          {projects?.map((project) => (
            <li key={project.id}>
              <Link 
                href={`/projects/${project.id}`}
                className="block p-2 rounded hover:bg-accent hover:text-accent-foreground"
              >
                {project.name}
              </Link>
            </li>
          ))}
        </ul>
      )}
      
      <div className="mt-8">
        <h3 className="text-sm font-semibold mb-2">最近のテスト実行</h3>
        {/* 最近のテスト実行リスト */}
      </div>
    </aside>
  );
}