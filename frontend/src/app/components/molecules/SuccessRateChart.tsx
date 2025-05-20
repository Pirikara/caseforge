"use client"

import React from 'react';
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  Tooltip, 
  Legend 
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TestCaseResult } from '@/hooks/useTestRuns';

interface SuccessRateChartProps {
  testCaseResults: TestCaseResult[];
}

export default function SuccessRateChart({ testCaseResults }: SuccessRateChartProps) {
  // 円グラフデータの作成
  const chartData = React.useMemo(() => {
    if (!testCaseResults || testCaseResults.length === 0) return [];
    
    const passedCount = testCaseResults.filter(r => r.status === 'passed').length;
    const failedCount = testCaseResults.filter(r => r.status === 'failed').length;
    const skippedCount = testCaseResults.filter(r => r.status === 'skipped').length;
    
    return [
      { name: '成功', value: passedCount, color: '#10b981' },
      { name: '失敗', value: failedCount, color: '#ef4444' },
      { name: 'スキップ', value: skippedCount, color: '#9ca3af' },
    ].filter(item => item.value > 0);
  }, [testCaseResults]);

  // 成功率の計算
  const successRate = React.useMemo(() => {
    if (!testCaseResults || testCaseResults.length === 0) return 0;
    const passedCount = testCaseResults.filter(r => r.status === 'passed').length;
    return Math.round((passedCount / testCaseResults.length) * 100);
  }, [testCaseResults]);

  // カスタムツールチップ
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-background p-3 border rounded-md shadow-md">
          <p className="font-medium">{`${payload[0].name}: ${payload[0].value}`}</p>
          <p className="text-sm text-muted-foreground">{`${Math.round((payload[0].value / testCaseResults.length) * 100)}%`}</p>
        </div>
      );
    }
    return null;
  };

  // カスタムラベル
  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index, name }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        className="text-xs font-medium"
      >
        {`${name} ${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>テスト成功率</span>
          <span className={`text-xl ${
            successRate > 80 ? 'text-green-600 dark:text-green-400' : 
            successRate > 50 ? 'text-yellow-600 dark:text-yellow-400' : 
            'text-red-600 dark:text-red-400'
          }`}>
            {successRate}%
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={renderCustomizedLabel}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend />
              </PieChart>
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
