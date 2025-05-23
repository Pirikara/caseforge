"use client"

import * as React from 'react';
import Link from 'next/link';
import { useServices } from '@/hooks/useServices';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { PlusIcon, SearchIcon } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ja } from 'date-fns/locale';

export default function ServicesPage() {
  const { services, isLoading, deleteService } = useServices(); // deleteService を取得
  const [searchQuery, setSearchQuery] = React.useState('');
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false); // state 定義を追加
  const [serviceToDelete, setServiceToDelete] = React.useState<string | null>(null); // state 定義を追加
  
  // 検索フィルター
  const filteredServices = React.useMemo(() => {
    if (!services) return [];
    
    return services.filter(service =>
      service.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (service.description && service.description.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  }, [services, searchQuery]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">すべてのサービス</h1>
        <Button asChild>
          <Link href="/services/new">
            <PlusIcon className="h-4 w-4 mr-2" />
            作成
          </Link>
        </Button>
      </div>
      
      <div className="flex items-center space-x-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="サービス名で検索..."
            className="pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      
      {isLoading ? (
        <div className="text-center py-6 md:py-8">読み込み中...</div>
      ) : filteredServices.length > 0 ? (
        <div className="rounded-md border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[300px]">サービス名</TableHead>
                <TableHead>説明</TableHead>
                <TableHead className="w-[150px]">作成日</TableHead>
                <TableHead className="w-[100px]">アクション</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredServices.map((service) => (
                <TableRow key={service.id}>
                  <TableCell className="font-medium">
                    <Link href={`/services/${service.id}`} className="hover:underline">
                      {service.name}
                    </Link>
                  </TableCell>
                  <TableCell>{service.description || '-'}</TableCell>
                  <TableCell>
                    {formatDistanceToNow(new Date(service.created_at), { addSuffix: true, locale: ja })}
                  </TableCell>
                  <TableCell className="flex items-center space-x-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/services/${service.id}`}>
                        詳細
                      </Link>
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => {
                        setServiceToDelete(service.id);
                        setShowDeleteDialog(true);
                      }}
                    >
                      削除
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        <div className="text-center py-8 border rounded-lg bg-background">
          <p className="text-muted-foreground">サービスが見つかりません</p>
          {searchQuery ? (
            <p className="mt-2">検索条件を変更してください</p>
          ) : (
            <p className="mt-2">新しいサービスを作成してください</p>
          )}
        </div>
      )}

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>サービスを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は元に戻せません。サービスに関連する全てのデータ（スキーマ、テストチェーン、実行結果など）が完全に削除されます。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (serviceToDelete) {
                  await deleteService(serviceToDelete);
                  setServiceToDelete(null);
                  setShowDeleteDialog(false);
                }
              }}
            >
              削除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
