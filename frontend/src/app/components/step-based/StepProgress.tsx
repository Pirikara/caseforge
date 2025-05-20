"use client"

import React from 'react';
import { useUIMode } from '@/contexts/UIModeContext';
import { cn } from '@/lib/utils';

interface StepProgressProps {
  className?: string;
}

export function StepProgress({ className }: StepProgressProps) {
  const { currentStep, totalSteps } = useUIMode();
  
  return (
    <div className={cn("w-full py-4", className)}>
      <div className="flex items-center justify-between">
        {/* ステップ表示 */}
        <div className="text-sm font-medium">
          ステップ {currentStep} / {totalSteps}
        </div>
        
        {/* 進捗率表示 */}
        <div className="text-sm text-muted-foreground">
          {Math.round((currentStep / totalSteps) * 100)}% 完了
        </div>
      </div>
      
      {/* プログレスバー */}
      <div className="mt-2 h-2 w-full rounded-full bg-secondary">
        <div 
          className="h-full rounded-full bg-primary transition-all duration-300 ease-in-out"
          style={{ width: `${(currentStep / totalSteps) * 100}%` }}
        />
      </div>
      
      {/* ステップインジケーター */}
      <div className="relative mt-4 flex justify-between">
        {Array.from({ length: totalSteps }).map((_, index) => {
          const stepNumber = index + 1;
          const isActive = stepNumber <= currentStep;
          const isCurrent = stepNumber === currentStep;
          
          return (
            <div key={index} className="flex flex-col items-center">
              <div 
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium",
                  isCurrent ? "ring-2 ring-primary ring-offset-2" : "",
                  isActive ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
                )}
              >
                {stepNumber}
              </div>
            </div>
          );
        })}
        
        {/* 接続線 */}
        <div className="absolute top-4 left-0 h-0.5 w-full -translate-y-1/2 bg-secondary -z-10" />
      </div>
    </div>
  );
}
