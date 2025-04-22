"use client"

import * as React from 'react';
import Link from 'next/link';
import { GithubIcon } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-border bg-background py-6">
      <div className="container flex flex-col md:flex-row items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          © {new Date().getFullYear()} Caseforge. All rights reserved.
        </p>
        <div className="flex items-center gap-4">
          <Link 
            href="https://github.com/yourusername/caseforge" 
            target="_blank"
            className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
          >
            <GithubIcon className="h-4 w-4" />
            GitHub
          </Link>
          <Link 
            href="/docs" 
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ドキュメント
          </Link>
        </div>
      </div>
    </footer>
  );
}