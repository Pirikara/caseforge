"use client"

import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StepResult } from '@/hooks/useTestRuns';

interface ResponseTimeChartProps {
  stepResults: StepResult[];
}

export default function ResponseTimeChart({ stepResults }: ResponseTimeChartProps) {
  // 棒グラフデータの作成
  const chartData = React.useMemo(() => {
    if (!stepResults || stepResults.length === 0) return [];
    
    // ステップをシーケンス順にソート
    const sortedSteps = [...stepResults].sort((a, b) => a.sequence - b.sequence);
    
    // 各ステップのレスポンスタイムをグラフデータに変換
    return sortedSteps.map(step => ({
      name: `ステップ ${step.sequence}`,
      method: step.method,
      path: step.path,
      responseTime: step.response_time || 0,
      passed: step.passed
    }));
  }, [stepResults]);

  // 平均レスポンスタイムの計算
  const averageResponseTime = React.useMemo(() => {
    if (!stepResults || stepResults.length === 0) return 0;
    const validTimes = stepResults.filter(s => s.response_time !== undefined).map(s => s.response_time as number);
    if (validTimes.length === 0) return 0;
    const sum = validTimes.reduce((acc, time) => acc + time, 0);
    return Math.round(sum / validTimes.length * 100) / 100; // 小数点2桁まで
  }, [stepResults]);

  // カスタムツールチップ
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-background p-3 border rounded-md shadow-md">
          <p className="font-medium">{label}</p>
          <p className="text-sm">{`${data.method} ${data.path}`}</p>
          <p className="text-sm text-muted-foreground">{`レスポンスタイム: ${data.responseTime.toFixed(2)} ms`}</p>
          <p className={`text-sm ${data.passed ? 'text-green-500' : 'text-red-500'}`}>
            {data.passed ? '成功' : '失敗'}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>レスポンスタイム</span>
          <span className="text-xl">
            平均: {averageResponseTime} ms
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{
                  top: 5,
                  right: 30,
                  left: 20,
                  bottom: 5,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis 
                  label={{ 
                    value: 'レスポンスタイム (ms)', 
                    angle: -90, 
                    position: 'insideLeft',
                    style: { textAnchor: 'middle' }
                  }} 
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Bar 
                  dataKey="responseTime" 
                  name="レスポンスタイム" 
                  fill="var(--chart-3)"
                  // 成功/失敗に応じて色を変える
                  fillOpacity={0.8}
                  stroke="var(--border)"
                  strokeWidth={1}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center">
              <p className="text-muted-foreground">データがありません</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
