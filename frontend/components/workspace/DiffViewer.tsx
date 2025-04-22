'use client';

import { DiffEditor, Monaco } from '@monaco-editor/react';
import { setupMonaco } from '@/lib/monacoSetup';

interface DiffViewerProps {
  original: string;
  modified: string;
  language?: string;
  originalLabel?: string;
  modifiedLabel?: string;
}

// Use monaco's diff editor to view created diffs 
export function DiffViewer({ 
  original, 
  modified, 
  language = 'based',
  originalLabel = 'Before', 
  modifiedLabel = 'After' 
}: DiffViewerProps) {
  if (!original && !modified) {
    return (
      <div className="p-4 text-muted-foreground">No diff to display.</div>
    );
  }

  function handleBeforeMount(monaco: Monaco) {
    setupMonaco(monaco);
  }

  return (
    <div className="w-full h-full overflow-auto flex flex-col">
      <div className="flex justify-between items-center px-6 py-2 border-b border-border bg-background/90 sticky top-0 z-10">
        <span className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">{originalLabel}</span>
        <span className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">{modifiedLabel}</span>
      </div>
      <div className="flex-1 min-h-[400px]">
        <DiffEditor
          height="100%"
          language={language}
          original={original}
          modified={modified}
          theme="based-theme"
          beforeMount={handleBeforeMount}
          options={{
            fontSize: 14,
            minimap: { enabled: false },
            fontFamily: 'monospace',
            scrollBeyondLastLine: false,
            renderSideBySide: true,
            readOnly: true,
            renderLineHighlight: 'all',
            renderIndicators: true,
            lineNumbers: 'on',
          }}
        />
      </div>
    </div>
  );
}