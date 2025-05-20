"use client"

import * as React from 'react';
import { Control, Controller, useFormContext, FieldValues, Path } from 'react-hook-form';
import { FormControl, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { PlusIcon, TrashIcon } from 'lucide-react';

interface PathParamEditorProps<TFieldValues extends FieldValues = FieldValues> {
  control: Control<TFieldValues>;
  name: Path<TFieldValues>;
}

export function PathParamEditor<TFieldValues extends FieldValues = FieldValues>({ name }: PathParamEditorProps<TFieldValues>) {
  const { control, watch, setValue } = useFormContext<TFieldValues>();
  const pathParams = watch(name) as Record<string, string> | undefined;

  const handleAddParam = () => {
    const currentParams = pathParams || {};
    const newKey = `new_param_${Date.now()}`;
    setValue(name, { ...currentParams, [newKey]: '' } as any);
  };

  const handleRemoveParam = (keyToRemove: string) => {
    const currentParams = pathParams || {};
    const { [keyToRemove]: _, ...rest } = currentParams;
    setValue(name, rest as any);
  };

  const handleKeyChange = (oldKey: string, newKey: string) => {
    const currentParams = pathParams || {};
    if (oldKey === newKey) return;

    const value = currentParams[oldKey];
    const { [oldKey]: _, ...rest } = currentParams;
    setValue(name, { ...rest, [newKey]: value } as any);
  };

  const handleValueChange = (key: string, newValue: string) => {
    const currentParams = pathParams || {};
    setValue(name, { ...currentParams, [key]: newValue } as any);
  };

  const paramKeys = Object.keys(pathParams || {});

  return (
    <Card>
      <CardContent className="pt-6">
        <FormItem>
          <FormLabel>パスパラメータ</FormLabel>
          <div className="text-sm text-muted-foreground mb-2">
            パスパラメータを指定します。例: <code>/users/{"{id}"}</code> の <code>&quot;{"{id}"}&quot;</code>
          </div>
          <FormControl>
            <div className="space-y-2">
              {paramKeys.map((key) => (
                <div key={key} className="flex items-center gap-2">
                  <Input
                    placeholder="キー"
                    value={key}
                    onChange={(e) => handleKeyChange(key, e.target.value)}
                  />
                  <Input
                    placeholder="値"
                    value={pathParams?.[key] || ''}
                    onChange={(e) => handleValueChange(key, e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => handleRemoveParam(key)}
                  >
                    <TrashIcon className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddParam}
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                パスパラメータを追加
              </Button>
            </div>
          </FormControl>
          <FormMessage />
        </FormItem>
      </CardContent>
    </Card>
  );
}
