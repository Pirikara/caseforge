"use client"

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useServices } from '@/hooks/useServices';
import { useTestRuns } from '@/hooks/useTestRuns';
import { TestCaseResult } from '@/hooks/useTestRuns';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  SearchIcon,
  PlayIcon,
  FileTextIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  BarChart3Icon
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { ja } from 'date-fns/locale';
import dynamic from 'next/dynamic';
import {
  ResponsiveContainer,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Bar
} from 'recharts';

const TestRunChart = dynamic(
  () => import('@/components/molecules/TestRunChart'),
  {
    ssr: false,
    loading: () => (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }
);

export default function TestRunsPage() {
  const params = useParams();
  const router = useRouter();
  const serviceId = params.id as string;
  
  const { services } = useServices();
  const { testRuns, isLoading } = useTestRuns(serviceId);
  
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState('all');
  
  const service = React.useMemo(() => {
    if (!services) return null;
    return services.find(p => p.id === serviceId);
  }, [services, serviceId]);
  
  const filteredTestRuns = React.useMemo(() => {
    if (!testRuns) return [];
    
    return testRuns.filter(run => {
      const matchesSearch = 
        run.run_id.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesStatus = statusFilter === 'all' || run.status === statusFilter;
      
      return matchesSearch && matchesStatus;
    });
  }, [testRuns, searchQuery, statusFilter]);
  
  const chartData = React.useMemo(() => {
    if (!testRuns || testRuns.length === 0) return [];
    
    const recentRuns = [...testRuns]
      .sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime())
      .slice(0, 10)
      .reverse();
    
    return recentRuns.map(run => {
      const totalTests = run.test_case_results?.reduce((sum, caseResult) => sum + (caseResult.step_results?.length || 0), 0) || 0;
      const passedTests = run.test_case_results?.reduce((sum, caseResult) => sum + (caseResult.step_results?.filter(step => step.passed).length || 0), 0) || 0;
      const failedTests = totalTests - passedTests;
      
      return {
        name: `#${run.run_id}`,
        成功: passedTests,
        失敗: failedTests,
      };
    });
  }, [testRuns]);
  
  if (!service) {
    return (
      <div className="text-center py-8">
        <p>サービスが見つかりません</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">テスト実行履歴</h1>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href={`/services/${serviceId}`}>
              <FileTextIcon className="h-4 w-4 mr-2" />
              サービス詳細
            </Link>
          </Button>
          <Button asChild>
            <Link href={`/services/${serviceId}/run`}>
              <PlayIcon className="h-4 w-4 mr-2" />
              テスト実行
            </Link>
          </Button>
        </div>
      </div>
      
      {/* グラフ */}
      {chartData.length > 0 && (
        <div className="border rounded-lg p-4 bg-background">
          <h2 className="text-lg font-semibold mb-4 flex items-center">
            <BarChart3Icon className="h-5 w-5 mr-2" />
            テスト実行結果の推移
          </h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="成功" stackId="a" fill="#10b981" />
                <Bar dataKey="失敗" stackId="a" fill="#ef4444" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      
      <div className="flex flex-col md:flex-row gap-4 items-end">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="実行IDで検索..."
            className="pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="w-full md:w-[200px]">
          <Select
            value={statusFilter}
            onValueChange={setStatusFilter}
          >
            <SelectTrigger>
              <SelectValue placeholder="ステータス" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">すべてのステータス</SelectItem>
              <SelectItem value="completed">完了</SelectItem>
              <SelectItem value="running">実行中</SelectItem>
              <SelectItem value="failed">失敗</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      
      {isLoading ? (
        <div className="text-center py-8">読み込み中...</div>
      ) : filteredTestRuns.length > 0 ? (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">実行ID</TableHead>
                <TableHead className="w-[120px]">ステータス</TableHead>
                <TableHead>開始時間</TableHead>
                <TableHead>終了時間</TableHead>
                <TableHead className="w-[120px]">テスト結果</TableHead>
                <TableHead className="w-[100px]">アクション</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTestRuns.map((run) => {
                const totalTests = run.test_case_results?.reduce((sum, caseResult) => sum + (caseResult.step_results?.length || 0), 0) || 0;
                const passedTests = run.test_case_results?.reduce((sum, caseResult) => sum + (caseResult.step_results?.filter(step => step.passed).length || 0), 0) || 0;
                const successRate = totalTests > 0 ? Math.round((passedTests / totalTests) * 100) : 0;
                
                return (
                  <TableRow key={run.id}>
                    <TableCell className="font-medium">#{run.run_id}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {run.status === 'completed' ? (
                          <CheckCircleIcon className="h-4 w-4 text-green-500" />
                        ) : run.status === 'failed' ? (
                          <XCircleIcon className="h-4 w-4 text-red-500" />
                        ) : (
                          <ClockIcon className="h-4 w-4 text-yellow-500" />
                        )}
                        <span>
                          {run.status === 'completed' ? '完了' : 
                           run.status === 'failed' ? '失敗' : '実行中'}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span>{format(new Date(run.start_time), 'yyyy/MM/dd HH:mm:ss')}</span>
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(run.start_time), { addSuffix: true, locale: ja })}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {run.end_time ? (
                        <div className="flex flex-col">
                          <span>{format(new Date(run.end_time), 'yyyy/MM/dd HH:mm:ss')}</span>
                          <span className="text-xs text-muted-foreground">
                            {formatDistanceToNow(new Date(run.end_time), { addSuffix: true, locale: ja })}
                          </span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {run.status === 'completed' ? (
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-green-500" 
                              style={{ width: `${successRate}%` }}
                            />
                          </div>
                          <span className="text-sm">{passedTests}/{totalTests}</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/services/${serviceId}/runs/${run.run_id}`}>
                          詳細
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      ) : (
        <div className="text-center py-8 border rounded-lg bg-background">
          <p className="text-muted-foreground">テスト実行履歴が見つかりません</p>
          {searchQuery || statusFilter !== 'all' ? (
            <p className="mt-2">検索条件を変更してください</p>
          ) : (
            <p className="mt-2">テスト実行を開始してください</p>
          )}
        </div>
      )}
    </div>
  );
}
