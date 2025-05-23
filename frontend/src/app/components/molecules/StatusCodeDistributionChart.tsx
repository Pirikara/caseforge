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
import { StepResult } from '@/hooks/useTestRuns';

interface StatusCodeDistributionChartProps {
  stepResults: StepResult[];
}

export default function StatusCodeDistributionChart({ stepResults }: StatusCodeDistributionChartProps) {
  const chartData = React.useMemo(() => {
    if (!stepResults || stepResults.length === 0) return [];
    
    const statusCodeGroups: Record<string, number> = {};
    
    stepResults.forEach(step => {
      if (step.status_code) {
        const statusGroup = getStatusCodeGroup(step.status_code);
        statusCodeGroups[statusGroup] = (statusCodeGroups[statusGroup] || 0) + 1;
      }
    });
    
    return Object.entries(statusCodeGroups).map(([group, count]) => ({
      name: group,
      value: count,
      color: getStatusCodeColor(group)
    }));
  }, [stepResults]);

  function getStatusCodeGroup(statusCode: number): string {
    if (statusCode >= 200 && statusCode < 300) return '2xx 成功';
    if (statusCode >= 300 && statusCode < 400) return '3xx リダイレクト';
    if (statusCode >= 400 && statusCode < 500) return '4xx クライアントエラー';
    if (statusCode >= 500) return '5xx サーバーエラー';
    return 'その他';
  }

  function getStatusCodeColor(group: string): string {
    if (group.startsWith('2xx')) return '#10b981';
    if (group.startsWith('3xx')) return '#3b82f6';
    if (group.startsWith('4xx')) return '#f59e0b';
    if (group.startsWith('5xx')) return '#ef4444';
    return '#9ca3af';
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const totalCount = stepResults.filter(s => s.status_code).length;
      const percentage = Math.round((payload[0].value / totalCount) * 100);
      
      return (
        <div className="bg-background p-3 border rounded-md shadow-md">
          <p className="font-medium">{`${payload[0].name}: ${payload[0].value}`}</p>
          <p className="text-sm text-muted-foreground">{`${percentage}%`}</p>
        </div>
      );
    }
    return null;
  };

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
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  const validStatusCodeCount = React.useMemo(() => {
    return stepResults.filter(s => s.status_code).length;
  }, [stepResults]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>ステータスコード分布</CardTitle>
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
              <p className="text-muted-foreground">
                {validStatusCodeCount === 0 ? 'ステータスコードデータがありません' : 'データがありません'}
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
