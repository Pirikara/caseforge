"use client"

import * as React from 'react';
import { MoonIcon, SunIcon, MenuIcon } from 'lucide-react';
import Link from 'next/link';
import { useTheme } from 'next-themes';
import { Button } from '../ui/button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger
} from '../ui/sheet';
import { Sidebar } from './Sidebar';
import { useState } from 'react';

export function Header() {
  const { theme, setTheme } = useTheme();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  
  return (
    <header className="border-b border-border bg-background">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex md:hidden">
            <Sheet open={isMenuOpen} onOpenChange={setIsMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MenuIcon className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="p-0">
                <SheetHeader className="p-4 border-b">
                  <SheetTitle>メニュー</SheetTitle>
                </SheetHeader>
                <div className="py-4">
                  <nav className="flex flex-col space-y-1 px-4">
                    <Link
                      href="/"
                      className="py-2 px-2 rounded-md hover:bg-accent"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      ダッシュボード
                    </Link>
                    <Link
                      href="/projects"
                      className="py-2 px-2 rounded-md hover:bg-accent"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      プロジェクト
                    </Link>
                    <Link
                      href="/docs"
                      className="py-2 px-2 rounded-md hover:bg-accent"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      ドキュメント
                    </Link>
                  </nav>
                </div>
                <div className="px-4 pt-4 border-t">
                  <Sidebar className="w-full border-none p-0" />
                </div>
              </SheetContent>
            </Sheet>
          </div>
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