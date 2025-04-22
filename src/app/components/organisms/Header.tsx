"use client"

import * as React from 'react';
import { MoonIcon, SunIcon } from 'lucide-react';
import Link from 'next/link';
import { useTheme } from 'next-themes';
import { Button } from '../ui/button';

export function Header() {
  const { theme, setTheme } = useTheme();
  
  return (
    <header className="border-b border-border bg-background">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-bold text-xl">Caseforge</Link>
          <nav className="hidden md:flex gap-4">
            <Link href="/" className="text-sm font-medium hover:text-primary">ダッシュボード</Link>
            <Link href="/projects" className="text-sm font-medium hover:text-primary">プロジェクト</Link>
            <Link href="/docs" className="text-sm font-medium hover:text-primary">ドキュメント</Link>
          </nav>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          {theme === 'dark' ? <SunIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}
        </Button>
      </div>
    </header>
  );
}