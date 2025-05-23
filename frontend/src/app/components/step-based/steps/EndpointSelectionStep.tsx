"use client"

import React, { useState, useEffect, useCallback } from 'react';
import { useUIMode } from '@/contexts/UIModeContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { Search, Filter, Check } from 'lucide-react';
import { fetcher } from '@/utils/fetcher';

interface Endpoint {
  id: string;
  path: string;
  method: string;
  summary?: string;
  description?: string;
}

export function EndpointSelectionStep() {
  const { sharedData, updateSharedData } = useUIMode();
  const serviceId = sharedData.serviceId;
  
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [selectedEndpoints, setSelectedEndpoints] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [methodFilter, setMethodFilter] = useState<string[]>([]);
  
  const fetchEndpoints = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetcher(`/api/services/${serviceId}/endpoints`);
      setEndpoints(data);

      if (sharedData.selectedEndpoints) {
        setSelectedEndpoints(sharedData.selectedEndpoints);
      }
    } catch (error) {
      toast.error("エンドポイント取得エラー", {
        description: "エンドポイント一覧の取得中にエラーが発生しました",
      });
    } finally {
      setIsLoading(false);
    }
  }, [serviceId, sharedData.selectedEndpoints]);

  useEffect(() => {
    if (serviceId) {
      fetchEndpoints();
    }
  }, [serviceId, fetchEndpoints]);
  
  const filteredEndpoints = endpoints.filter(endpoint => {
    const matchesSearch = 
      searchQuery === '' || 
      endpoint.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (endpoint.summary && endpoint.summary.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesMethod = 
      methodFilter.length === 0 || 
      methodFilter.includes(endpoint.method.toUpperCase());
    
    return matchesSearch && matchesMethod;
  });
  
  const availableMethods = Array.from(new Set(endpoints.map(e => e.method.toUpperCase())));
  
  const toggleEndpoint = (endpointId: string) => {
    setSelectedEndpoints(prev => {
      if (prev.includes(endpointId)) {
        return prev.filter(id => id !== endpointId);
      } else {
        return [...prev, endpointId];
      }
    });
  };
  
  const toggleAll = () => {
    if (selectedEndpoints.length === filteredEndpoints.length) {
      setSelectedEndpoints([]);
    } else {
      setSelectedEndpoints(filteredEndpoints.map(e => e.id));
    }
  };
  
  const toggleMethodFilter = (method: string) => {
    setMethodFilter(prev => {
      if (prev.includes(method)) {
        return prev.filter(m => m !== method);
      } else {
        return [...prev, method];
      }
    });
  };
  
  const saveSelection = () => {
    updateSharedData('selectedEndpoints', selectedEndpoints);
    
    toast.success("エンドポイントを選択しました", {
      description: `${selectedEndpoints.length}個のエンドポイントが選択されました`,
    });
  };
  
  const getMethodColor = (method: string) => {
    switch (method.toUpperCase()) {
      case 'GET': return 'bg-blue-100 text-blue-800';
      case 'POST': return 'bg-green-100 text-green-800';
      case 'PUT': return 'bg-amber-100 text-amber-800';
      case 'DELETE': return 'bg-red-100 text-red-800';
      case 'PATCH': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>テスト対象エンドポイントの選択</CardTitle>
        <CardDescription>
          テストを生成するAPIエンドポイントを選択してください
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-grow">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="エンドポイントを検索..."
              className="pl-8"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          
          <div className="flex gap-2 flex-wrap">
            {availableMethods.map(method => (
              <Button
                key={method}
                variant="outline"
                size="sm"
                className={`${methodFilter.includes(method) ? 'bg-primary/20' : ''}`}
                onClick={() => toggleMethodFilter(method)}
              >
                {method}
              </Button>
            ))}
          </div>
        </div>
        
        <div className="flex justify-between items-center">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleAll}
          >
            {selectedEndpoints.length === filteredEndpoints.length ? '全て解除' : '全て選択'}
          </Button>
          
          <span className="text-sm text-muted-foreground">
            {selectedEndpoints.length} / {endpoints.length} 選択中
          </span>
        </div>
        
        {isLoading ? (
          <div className="py-8 text-center">
            <p className="text-muted-foreground">読み込み中...</p>
          </div>
        ) : endpoints.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-muted-foreground">エンドポイントが見つかりません</p>
            <p className="text-sm text-muted-foreground mt-2">
              先にOpenAPIスキーマをアップロードしてください
            </p>
          </div>
        ) : (
          <div className="border rounded-md divide-y">
            {filteredEndpoints.map(endpoint => (
              <div 
                key={endpoint.id}
                className="flex items-start p-3 hover:bg-muted/50 cursor-pointer"
                onClick={() => toggleEndpoint(endpoint.id)}
              >
                <Checkbox
                  checked={selectedEndpoints.includes(endpoint.id)}
                  onCheckedChange={() => toggleEndpoint(endpoint.id)}
                  className="mt-1 mr-3"
                />
                
                <div className="flex-grow">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${getMethodColor(endpoint.method)}`}>
                      {endpoint.method.toUpperCase()}
                    </span>
                    <span className="font-mono text-sm">{endpoint.path}</span>
                  </div>
                  
                  {endpoint.summary && (
                    <p className="text-sm text-muted-foreground">{endpoint.summary}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        
        <Button 
          className="w-full mt-4" 
          onClick={saveSelection}
          disabled={selectedEndpoints.length === 0}
        >
          選択したエンドポイントを保存
        </Button>
      </CardContent>
    </Card>
  );
}
