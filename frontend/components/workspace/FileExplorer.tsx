'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Folder, File } from 'lucide-react';
import { cn } from '@/lib/utils';

type FileExplorerProps = {
  files: string[];
  activeFile: string | null;
  onSelectFile: (filename: string) => void;
};

export function FileExplorer({
  files,
  activeFile,
  onSelectFile,
}: FileExplorerProps) {
  return (
    <div className="h-full flex flex-col bg-background">
      <div className="flex items-center justify-between p-2 border-b border-border">
        <h2 className="text-sm font-medium">EXPLORER</h2>
      </div>
      
      <div className="px-1 py-2">
        <div className="flex items-center text-xs text-muted-foreground gap-1 pl-2 py-1">
          <Folder className="h-3.5 w-3.5" />
          <span>WORKSPACE</span>
        </div>
        
        <div className="space-y-0.5 mt-1">
          {files.map((file) => (
            <button
              key={file}
              className={cn(
                "w-full flex items-center px-2 py-1 text-xs rounded-sm text-left gap-1.5",
                activeFile === file
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-accent/50 hover:text-accent-foreground"
              )}
              onClick={() => onSelectFile(file)}
            >
              <File className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{file}</span>
            </button>
          ))}
          
          {files.length === 0 && (
            <div className="px-2 py-3 text-xs text-muted-foreground">
              Use the chat to create your first file!
            </div>
          )}
        </div>
      </div>
    </div>
  );
}