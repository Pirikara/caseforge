"use client"

import * as React from 'react';
import { Control, Controller, useFormContext, FieldValues, Path } from 'react-hook-form';
import { FormControl, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { PlusIcon, TrashIcon } from 'lucide-react';

interface ExtractorEditorProps<TFieldValues extends FieldValues = FieldValues> {
  control: Control<TFieldValues>;
  name: Path<TFieldValues>;
}

export function ExtractorEditor<TFieldValues extends FieldValues = FieldValues>({ name }: ExtractorEditorProps<TFieldValues>) {
  const { control, watch, setValue } = useFormContext<TFieldValues>();
  const extractRules = watch(name) as Record<string, string> | undefined;

  const handleAddRule = () => {
    const currentRules = extractRules || {};
    const newKey = `new_rule_${Date.now()}`;
    setValue(name, { ...currentRules, [newKey]: '' } as any);
  };

  const handleRemoveRule = (keyToRemove: string) => {
    const currentRules = extractRules || {};
    const { [keyToRemove]: _, ...rest } = currentRules;
    setValue(name, rest as any);
  };

  const handleKeyChange = (oldKey: string, newKey: string) => {
    const currentRules = extractRules || {};
    if (oldKey === newKey) return;

    const value = currentRules[oldKey];
    const { [oldKey]: _, ...rest } = currentRules;
    setValue(name, { ...rest, [newKey]: value } as any);
  };

  const handleValueChange = (key: string, newValue: string) => {
    const currentRules = extractRules || {};
    setValue(name, { ...currentRules, [key]: newValue } as any);
  };

  const ruleKeys = Object.keys(extractRules || {});

  return (
    <Card>
      <CardContent className="pt-6">
        <FormItem>
          <FormLabel>変数抽出ルール</FormLabel>
          <div className="text-sm text-muted-foreground mb-2">
            レスポンスから変数を抽出するためのJSONPathを指定します。
            例: $.data.id → data.id の値を抽出
          </div>
          <FormControl>
            <div className="space-y-2">
              {ruleKeys.map((key) => (
                <div key={key} className="flex items-center gap-2">
                  <Input
                    placeholder="変数名"
                    value={key}
                    onChange={(e) => handleKeyChange(key, e.target.value)}
                  />
                  <Input
                    placeholder="JSONPath (例: $.data.id)"
                    value={extractRules?.[key] || ''}
                    onChange={(e) => handleValueChange(key, e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => handleRemoveRule(key)}
                  >
                    <TrashIcon className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddRule}
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                抽出ルールを追加
              </Button>
            </div>
          </FormControl>
          <FormMessage />
        </FormItem>
      </CardContent>
    </Card>
  );
}
