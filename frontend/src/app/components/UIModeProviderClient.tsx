"use client"

import * as React from 'react';
import { UIModeProvider } from '../contexts/UIModeContext';

interface UIModeProviderClientProps {
  children: React.ReactNode;
}

export function UIModeProviderClient({ children }: UIModeProviderClientProps) {
  return <UIModeProvider>{children}</UIModeProvider>;
}
