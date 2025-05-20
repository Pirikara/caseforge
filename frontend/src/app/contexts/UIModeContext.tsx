"use client"

import React, { createContext, useContext, useState, ReactNode } from 'react';

// UIモードの種類を定義
export type UIMode = 'step-based' | 'management';

// コンテキストの型定義
interface UIModeContextType {
  mode: UIMode;
  setMode: (mode: UIMode) => void;
  // ステップベースモードの状態
  currentStep: number;
  setCurrentStep: (step: number) => void;
  totalSteps: number;
  setTotalSteps: (total: number) => void;
  // 共有データ
  sharedData: Record<string, any>;
  updateSharedData: (key: string, value: any) => void;
}

// コンテキストの作成
const UIModeContext = createContext<UIModeContextType | undefined>(undefined);

// プロバイダーコンポーネント
export function UIModeProvider({ children }: { children: ReactNode }) {
  // UIモードの状態
  const [mode, setMode] = useState<UIMode>('management');
  
  // ステップベースモードの状態
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [totalSteps, setTotalSteps] = useState<number>(5); // デフォルトは5ステップ
  
  // モード間で共有するデータ
  const [sharedData, setSharedData] = useState<Record<string, any>>({});
  
  // 共有データを更新する関数
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

// カスタムフック
export function useUIMode() {
  const context = useContext(UIModeContext);
  if (context === undefined) {
    throw new Error('useUIMode must be used within a UIModeProvider');
  }
  return context;
}
