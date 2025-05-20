"use client"

import * as React from 'react';
import { Control, Controller, useFieldArray } from 'react-hook-form';
import { FormControl, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { PlusIcon, TrashIcon } from 'lucide-react';

interface HeaderEditorProps {
  control: Control<any>;
  name: string;
}

export function HeaderEditor({ control, name }: HeaderEditorProps) {
  // useFieldArrayを使用してヘッダーの配列を管理
  const { fields, append, remove, update } = useFieldArray({
    control,
    name: name, // 親から渡されるフィールド名を使用
  });

  // オブジェクトから配列への変換と、配列からオブジェクトへの変換を行う
  const convertObjectToArray = (obj: Record<string, string> = {}) => {
    return Object.entries(obj).map(([key, value]) => ({ key, value }));
  };

  const convertArrayToObject = (arr: { key: string; value: string }[]) => {
    return arr.reduce((acc, { key, value }) => {
      if (key) {
        acc[key] = value;
      }
      return acc;
    }, {} as Record<string, string>);
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <Controller
          control={control}
          name={name}
          render={({ field }) => {
            // オブジェクトを配列に変換してuseFieldArrayのfieldsを初期化
            React.useEffect(() => {
              if (field.value && Object.keys(field.value).length > 0 && fields.length === 0) {
                const headersArray = convertObjectToArray(field.value);
                append(headersArray);
              } else if ((!field.value || Object.keys(field.value).length === 0) && fields.length > 0) {
                 // field.value が空になったら fields もクリア
                 remove(fields.map((_, index) => index));
              }
            }, [field.value, fields.length, append, remove]);


            // fields の変更を親フォームに通知
            React.useEffect(() => {
              field.onChange(convertArrayToObject(fields));
            }, [fields, field.onChange]);


            return (
              <FormItem>
                <FormLabel>リクエストヘッダー</FormLabel>
                <FormControl>
                  <div className="space-y-2">
                    {fields.map((item, index) => (
                      <div key={item.id} className="flex items-center gap-2">
                        <Input
                          placeholder="ヘッダー名"
                          value={item.key}
                          onChange={(e) => update(index, { ...item, key: e.target.value })}
                        />
                        <Input
                          placeholder="値"
                          value={item.value}
                          onChange={(e) => update(index, { ...item, value: e.target.value })}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => remove(index)}
                        >
                          <TrashIcon className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => append({ key: '', value: '' })}
                    >
                      <PlusIcon className="h-4 w-4 mr-1" />
                      ヘッダーを追加
                    </Button>
                  </div>
                </FormControl>
                <FormMessage />
              </FormItem>
            );
          }}
        />
      </CardContent>
    </Card>
  );
}
