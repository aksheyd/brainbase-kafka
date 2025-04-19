'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Folder, File, Plus, X } from 'lucide-react';
import { cn } from '@/lib/utils';

type FileExplorerProps = {
  files: string[];
  activeFile: string | null;
  onSelectFile: (filename: string) => void;
  onCreateFile: (filename: string) => void;
};

export function FileExplorer({
  files,
  activeFile,
  onSelectFile,
  onCreateFile
}: FileExplorerProps) {
  const [isCreatingFile, setIsCreatingFile] = useState(false);
  const [newFileName, setNewFileName] = useState('');

  const handleCreateFile = () => {
    if (newFileName.trim()) {
      onCreateFile(newFileName.trim());
      setNewFileName('');
      setIsCreatingFile(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="flex items-center justify-between p-2 border-b border-border">
        <h2 className="text-sm font-medium">EXPLORER</h2>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => setIsCreatingFile(true)}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      
      <div className="px-1 py-2">
        <div className="flex items-center text-xs text-muted-foreground gap-1 pl-2 py-1">
          <Folder className="h-3.5 w-3.5" />
          <span>WORKSPACE</span>
        </div>
        
        {isCreatingFile && (
          <div className="flex items-center p-1 gap-1">
            <Input
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              placeholder="filename.based"
              className="h-7 text-xs"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleCreateFile();
                } else if (e.key === 'Escape') {
                  setIsCreatingFile(false);
                }
              }}
            />
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setIsCreatingFile(false)}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
        
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
          
          {files.length === 0 && !isCreatingFile && (
            <div className="px-2 py-3 text-xs text-muted-foreground">
              No files yet. Create a new file to get started or use the chat!
            </div>
          )}
        </div>
      </div>
    </div>
  );
}