"use client"

import * as React from 'react';
import { MenuIcon, XIcon } from 'lucide-react';
import Link from 'next/link';
import { Button } from '../ui/button';
import { cn } from '@/lib/utils';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetClose
} from '../ui/sheet';
import { Sidebar } from './Sidebar';
import { useState } from 'react';

export function Header({ className }: { className?: string }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  
  return (
    <header className={cn("border-b border-border bg-background", className)}>
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex">
            <Sheet open={isMenuOpen} onOpenChange={setIsMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MenuIcon className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="p-0 w-64">
                <SheetHeader className="p-4 border-b">
                  <div className="flex items-center justify-between">
                    <SheetTitle>メニュー</SheetTitle>
                    <SheetClose className="rounded-full hover:bg-muted p-2 transition-colors">
                      <XIcon className="h-4 w-4" />
                    </SheetClose>
                  </div>
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
                      href="/services"
                      className="py-2 px-2 rounded-md hover:bg-accent"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      サービス
                    </Link>
                  </nav>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </header>
  );
}
