"use client"

import React, { ReactNode } from 'react';
import { useUIMode } from '@/contexts/UIModeContext';
import { StepProgress } from './StepProgress';
import { Button } from '@/components/ui/button';
import { ArrowLeft, ArrowRight, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StepBasedUIProps {
  className?: string;
  children: ReactNode;
  onComplete?: () => void;
}

export function StepBasedUI({ className, children, onComplete }: StepBasedUIProps) {
  const { currentStep, setCurrentStep, totalSteps } = useUIMode();
  
  // 子要素を配列として扱い、現在のステップに対応する子要素のみを表示
  const childrenArray = React.Children.toArray(children);
  
  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };
  
  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };
  
  const handleComplete = () => {
    if (onComplete) {
      onComplete();
    }
  };
  
  return (
    <div className={cn("space-y-6", className)}>
      {/* ステップ進捗表示 */}
      <StepProgress />
      
      {/* 現在のステップのコンテンツ */}
      <div className="min-h-[400px] p-4 border rounded-lg bg-card">
        {childrenArray[currentStep - 1] || (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground">このステップのコンテンツがありません</p>
          </div>
        )}
      </div>
      
      {/* ナビゲーションボタン */}
      <div className="flex justify-between pt-4">
        <Button
          variant="outline"
          onClick={handlePrevious}
          disabled={currentStep === 1}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          前へ
        </Button>
        
        {currentStep < totalSteps ? (
          <Button onClick={handleNext}>
            次へ
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleComplete} variant="default">
            完了
            <Check className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
