'use client';

import MonacoEditor, { Monaco } from '@monaco-editor/react';
import { setupMonaco } from '@/lib/monacoSetup'; // Import the setup function

interface EditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  options?: Record<string, any>;
}

// Use Monaco editor with 'based' language and theme
export function Editor({ value, onChange, language = 'based', options }: EditorProps) {
  function handleBeforeMount(monaco: Monaco) {
    setupMonaco(monaco);
  }

  return (
    <div className="w-full h-full overflow-auto">
      <MonacoEditor
        height="100%"
        defaultLanguage={language}
        value={value}
        onChange={(val) => onChange(val ?? '')}
        theme="based-theme"
        beforeMount={handleBeforeMount}
        options={{
          fontSize: 14,
          minimap: { enabled: false },
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
          scrollBeyondLastLine: true,
          automaticLayout: true,
          wordWrap: 'on',
          lineNumbers: 'on',
          tabSize: 2,
          renderLineHighlight: 'all',
          ...options,
        }}
      />
    </div>
  );
}