"use client"

import React from 'react';
import { useUIMode } from '@/contexts/UIModeContext';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Layers, ListChecks } from 'lucide-react';

interface ModeToggleProps {
  className?: string;
}

export function ModeToggle({ className }: ModeToggleProps) {
  const { mode, setMode } = useUIMode();
  
  const handleModeChange = (value: string) => {
    setMode(value as 'step-based' | 'management');
  };
  
  return (
    <div className={className}>
      <Tabs
        value={mode}
        onValueChange={handleModeChange}
        className="w-full"
      >
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="step-based" className="flex items-center gap-2">
            <ListChecks className="h-4 w-4" />
            <span>ステップモード</span>
            {mode === 'step-based' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary transition-opacity duration-200" />
            )}
          </TabsTrigger>
          <TabsTrigger value="management" className="flex items-center gap-2">
            <Layers className="h-4 w-4" />
            <span>管理モード</span>
            {mode === 'management' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary transition-opacity duration-200" />
            )}
          </TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
  );
}

export function ModeToggleCompact({ className }: ModeToggleProps) {
  const { mode, setMode } = useUIMode();
  
  const toggleMode = () => {
    setMode(mode === 'step-based' ? 'management' : 'step-based');
  };
  
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={toggleMode}
      className={className}
    >
      {mode === 'step-based' ? (
        <>
          <Layers className="mr-2 h-4 w-4" />
          管理モードに切替
        </>
      ) : (
        <>
          <ListChecks className="mr-2 h-4 w-4" />
          ステップモードに切替
        </>
      )}
    </Button>
  );
}
