"use client"

import * as React from 'react';
import { Control, Controller } from 'react-hook-form';
import { FormControl, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Card, CardContent } from '@/components/ui/card';
import Editor from '@monaco-editor/react';

interface ResponseValidatorProps {
  control: Control<any>;
  name: string;
}

export function ResponseValidator({ control, name }: ResponseValidatorProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        <Controller
          control={control}
          name={name}
          render={({ field }) => (
            <FormItem>
              <FormLabel>期待するレスポンス (JSON)</FormLabel>
              <FormControl>
                <Editor
                  height="300px"
                  defaultLanguage="json"
                  value={field.value ? JSON.stringify(field.value, null, 2) : ''}
                  onChange={(value: string | undefined) => {
                    try {
                      if (!value || value.trim() === '') {
                        field.onChange(null);
                        return;
                      }
                      const parsedValue = JSON.parse(value);
                      field.onChange(parsedValue);
                    } catch (e) {
                      console.error('JSON parse error:', e);
                    }
                  }}
                  options={{
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    lineNumbers: 'on',
                    automaticLayout: true,
                  }}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </CardContent>
    </Card>
  );
}
