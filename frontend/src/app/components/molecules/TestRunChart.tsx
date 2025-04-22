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

interface TestRunChartProps {
  data: {
    name: string;
    passed: number;
    failed: number;
  }[];
}

export default function TestRunChart({ data }: TestRunChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart
        data={data}
        margin={{
          top: 20,
          right: 30,
          left: 20,
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: 'var(--background)',
            borderColor: 'var(--border)',
            color: 'var(--foreground)'
          }}
        />
        <Legend />
        <Bar dataKey="passed" fill="var(--chart-2)" name="成功" />
        <Bar dataKey="failed" fill="var(--chart-5)" name="失敗" />
      </BarChart>
    </ResponsiveContainer>
  );
}