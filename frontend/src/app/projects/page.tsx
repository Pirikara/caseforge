"use client"

import * as React from 'react';
import Link from 'next/link';
import { useProjects } from '@/hooks/useProjects';
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

export default function ProjectsPage() {
  const { projects, isLoading, deleteProject } = useProjects(); // deleteProject を取得
  const [searchQuery, setSearchQuery] = React.useState('');
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false); // state 定義を追加
  const [projectToDelete, setProjectToDelete] = React.useState<string | null>(null); // state 定義を追加
  
  // 検索フィルター
  const filteredProjects = React.useMemo(() => {
    if (!projects) return [];
    
    return projects.filter(project =>
      project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (project.description && project.description.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  }, [projects, searchQuery]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">プロジェクト一覧</h1>
        <Button asChild>
          <Link href="/projects/new">
            <PlusIcon className="h-4 w-4 mr-2" />
            新規プロジェクト
          </Link>
        </Button>
      </div>
      
      <div className="flex items-center space-x-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="プロジェクト名で検索..."
            className="pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      
      {isLoading ? (
        <div className="text-center py-6 md:py-8">読み込み中...</div>
      ) : filteredProjects.length > 0 ? (
        <div className="rounded-md border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[300px]">プロジェクト名</TableHead>
                <TableHead>説明</TableHead>
                <TableHead className="w-[150px]">作成日</TableHead>
                <TableHead className="w-[100px]">アクション</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredProjects.map((project) => (
                <TableRow key={project.id}>
                  <TableCell className="font-medium">
                    <Link href={`/projects/${project.id}`} className="hover:underline">
                      {project.name}
                    </Link>
                  </TableCell>
                  <TableCell>{project.description || '-'}</TableCell>
                  <TableCell>
                    {formatDistanceToNow(new Date(project.created_at), { addSuffix: true, locale: ja })}
                  </TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/projects/${project.id}`}>
                        詳細
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        <div className="text-center py-8 border rounded-lg bg-background">
          <p className="text-muted-foreground">プロジェクトが見つかりません</p>
          {searchQuery ? (
            <p className="mt-2">検索条件を変更してください</p>
          ) : (
            <p className="mt-2">新しいプロジェクトを作成してください</p>
          )}
        </div>
      )}

      {/* 削除確認ダイアログ */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>プロジェクトを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は元に戻せません。プロジェクトに関連する全てのデータ（スキーマ、テストチェーン、実行結果など）が完全に削除されます。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (projectToDelete) {
                  await deleteProject(projectToDelete);
                  setProjectToDelete(null);
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