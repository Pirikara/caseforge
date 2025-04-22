"use client"

import * as React from 'react';
import { UploadIcon, XIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface FileUploadProps {
  accept?: string;
  maxSize?: number; // in MB
  onFileSelect: (file: File) => void;
}

export function FileUpload({ accept = '*', maxSize = 5, onFileSelect }: FileUploadProps) {
  const [file, setFile] = React.useState<File | null>(null);
  const [isDragging, setIsDragging] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    validateAndSetFile(selectedFile);
  };
  
  const validateAndSetFile = (selectedFile: File | undefined) => {
    setError(null);
    
    if (!selectedFile) return;
    
    // ファイルサイズのチェック
    if (selectedFile.size > maxSize * 1024 * 1024) {
      setError(`ファイルサイズは${maxSize}MB以下である必要があります`);
      return;
    }
    
    setFile(selectedFile);
    onFileSelect(selectedFile);
  };
  
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };
  
  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };
  
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    const selectedFile = e.dataTransfer.files?.[0];
    validateAndSetFile(selectedFile);
  };
  
  const handleRemoveFile = () => {
    setFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };
  
  return (
    <div className="space-y-2">
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center ${
          isDragging ? 'border-primary bg-primary/5' : 'border-border'
        } ${error ? 'border-destructive bg-destructive/5' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <Input
          type="file"
          accept={accept}
          onChange={handleFileChange}
          className="hidden"
          ref={fileInputRef}
        />
        
        {file ? (
          <div className="flex items-center justify-between p-2 bg-background rounded">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-primary/10 rounded">
                <UploadIcon className="h-5 w-5 text-primary" />
              </div>
              <div className="text-left">
                <p className="font-medium truncate max-w-[200px]">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRemoveFile}
              className="text-muted-foreground hover:text-foreground"
            >
              <XIcon className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <div className="py-4">
            <UploadIcon className="h-10 w-10 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm font-medium mb-1">
              ファイルをドラッグ＆ドロップするか、クリックしてアップロード
            </p>
            <p className="text-xs text-muted-foreground mb-3">
              最大ファイルサイズ: {maxSize}MB
            </p>
            <Button type="button" variant="outline" onClick={handleButtonClick}>
              ファイルを選択
            </Button>
          </div>
        )}
      </div>
      
      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
    </div>
  );
}