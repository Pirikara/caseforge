"use client"

import * as React from 'react';
import { Control, Controller, useFieldArray, useFormContext, FieldValues } from 'react-hook-form';
import { FormControl, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { PlusIcon, TrashIcon } from 'lucide-react';

interface QueryParamEditorProps {
  name: string;
  control: Control<{
    path: string;
    method: string;
    expected_status: number;
    name?: string | undefined;
    request_body?: any;
    request_headers?: Record<string, string> | undefined;
    expected_response?: any;
    path_params?: Record<string, string> | undefined;
    query_params?: Record<string, string> | undefined;
    extract_rules?: Record<string, string> | undefined;
  }, any>;
}

export function QueryParamEditor({ name }: QueryParamEditorProps) {
  const { control, watch, setValue } = useFormContext();
  const { fields, append, remove, update } = useFieldArray({
    control,
    name: name,
  });

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

  const queryParams = watch(name);

  React.useEffect(() => {
    const paramsArray = convertObjectToArray(queryParams);
    if (JSON.stringify(fields.map(item => ({ key: (item as any).key, value: (item as any).value }))) !== JSON.stringify(paramsArray)) {
       remove(fields.map((_, index) => index));
       if (paramsArray.length > 0) {
         append(paramsArray);
       }
    }
  }, [queryParams, fields, append, remove]);

  React.useEffect(() => {
    const queryParamsObject = convertArrayToObject(fields.map(item => ({ key: (item as any).key, value: (item as any).value })));
    if (JSON.stringify(watch(name)) !== JSON.stringify(queryParamsObject)) {
      setValue(name, queryParamsObject, { shouldDirty: true });
    }
  }, [fields, name, setValue, watch]);


  return (
    <Card>
      <CardContent className="pt-6">
        <Controller
          control={control}
          name={name}
          render={() => (
            <FormItem>
              <FormLabel>クエリパラメータ</FormLabel>
              <FormControl>
                <div className="space-y-2">
                  {fields.map((item, index) => (
                    <div key={item.id} className="flex items-center gap-2">
                      <Input
                        placeholder="パラメータ名"
                        value={(item as any).key}
                        onChange={(e) => update(index, { ...item, key: e.target.value })}
                      />
                      <Input
                        placeholder="値"
                        value={(item as any).value}
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
                    onClick={() => append({ key: '', value: '' } as any)}
                  >
                    <PlusIcon className="h-4 w-4 mr-1" />
                    クエリパラメータを追加
                  </Button>
                </div>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </CardContent>
    </Card>
  );
}
