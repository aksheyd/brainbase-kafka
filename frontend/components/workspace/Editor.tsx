'use client';

import { useRef } from 'react';
import MonacoEditor from '@monaco-editor/react';
import { setupMonaco } from '@/lib/monacoSetup'; // Import the setup function

interface EditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
}

export function Editor({ value, onChange, language = 'based' }: EditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);

  // Use the shared setup function
  function handleBeforeMount(monaco: any) {
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
        }}
      />
    </div>
  );
}