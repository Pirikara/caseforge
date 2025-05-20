"use client"

import React, { createContext, useContext, useState, ReactNode } from 'react';

export type UIMode = 'step-based' | 'management';

interface UIModeContextType {
  mode: UIMode;
  setMode: (mode: UIMode) => void;
  currentStep: number;
  setCurrentStep: (step: number) => void;
  totalSteps: number;
  setTotalSteps: (total: number) => void;
  sharedData: Record<string, any>;
  updateSharedData: (key: string, value: any) => void;
}

const UIModeContext = createContext<UIModeContextType | undefined>(undefined);

export function UIModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<UIMode>('management');
  
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [totalSteps, setTotalSteps] = useState<number>(5);
  
  const [sharedData, setSharedData] = useState<Record<string, any>>({});
  
  const updateSharedData = (key: string, value: any) => {
    setSharedData(prev => ({
      ...prev,
      [key]: value
    }));
  };

  return (
    <UIModeContext.Provider
      value={{
        mode,
        setMode,
        currentStep,
        setCurrentStep,
        totalSteps,
        setTotalSteps,
        sharedData,
        updateSharedData
      }}
    >
      {children}
    </UIModeContext.Provider>
  );
}

export function useUIMode() {
  const context = useContext(UIModeContext);
  if (context === undefined) {
    throw new Error('useUIMode must be used within a UIModeProvider');
  }
  return context;
}
