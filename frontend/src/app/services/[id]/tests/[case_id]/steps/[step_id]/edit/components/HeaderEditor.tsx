"use client"

import * as React from 'react';
import { Control, Controller, useFormContext, FieldValues, Path } from 'react-hook-form';
import { FormControl, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { PlusIcon, TrashIcon } from 'lucide-react';

interface HeaderEditorProps<TFieldValues extends FieldValues = FieldValues> {
  control: Control<TFieldValues>;
  name: Path<TFieldValues>;
}

export function HeaderEditor<TFieldValues extends FieldValues = FieldValues>({ name }: HeaderEditorProps<TFieldValues>) {
  const { control, watch, setValue } = useFormContext<TFieldValues>();
  const headers = watch(name) as Record<string, string> | undefined;

  const handleAddHeader = () => {
    const currentHeaders = headers || {};
    const newKey = `new_header_${Date.now()}`;
    setValue(name, { ...currentHeaders, [newKey]: '' } as any);
  };

  const handleRemoveHeader = (keyToRemove: string) => {
    const currentHeaders = headers || {};
    const { [keyToRemove]: _, ...rest } = currentHeaders;
    setValue(name, rest as any);
  };

  const handleKeyChange = (oldKey: string, newKey: string) => {
    const currentHeaders = headers || {};
    if (oldKey === newKey) return;

    const value = currentHeaders[oldKey];
    const { [oldKey]: _, ...rest } = currentHeaders;
    setValue(name, { ...rest, [newKey]: value } as any);
  };

  const handleValueChange = (key: string, newValue: string) => {
    const currentHeaders = headers || {};
    setValue(name, { ...currentHeaders, [key]: newValue } as any);
  };

  const headerKeys = Object.keys(headers || {});

  return (
    <Card>
      <CardContent className="pt-6">
        <FormItem>
          <FormLabel>ヘッダー</FormLabel>
          <div className="text-sm text-muted-foreground mb-2">
            リクエストヘッダーを指定します。
          </div>
          <FormControl>
            <div className="space-y-2">
              {headerKeys.map((key) => (
                <div key={key} className="flex items-center gap-2">
                  <Input
                    placeholder="キー"
                    value={key}
                    onChange={(e) => handleKeyChange(key, e.target.value)}
                  />
                  <Input
                    placeholder="値"
                    value={headers?.[key] || ''}
                    onChange={(e) => handleValueChange(key, e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => handleRemoveHeader(key)}
                  >
                    <TrashIcon className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddHeader}
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                ヘッダーを追加
              </Button>
            </div>
          </FormControl>
          <FormMessage />
        </FormItem>
      </CardContent>
    </Card>
  );
}
