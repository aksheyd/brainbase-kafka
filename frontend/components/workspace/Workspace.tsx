'use client';

import { useState, useEffect } from 'react';
import { Editor } from '@/components/workspace/Editor';
import { DiffViewer } from '@/components/workspace/DiffViewer';
import { Button } from '@/components/ui/button';
import { Check, X } from 'lucide-react';

type WorkspaceProps = {
  filename: string | null;
  content: string;
  editorValue: string;
  diff: string | null;
  oldCode?: string | null;
  newCode?: string | null;
  onClearDiff: () => void;
  onSave: (filename: string, content: string) => void;
  sendMessage: (message: any) => void;
  validationError?: string | null;
  onEditorValueChange?: (value: string) => void;
  isProcessing: boolean;
  isDiffPending: boolean;
};

export function Workspace({ 
  filename, 
  content, 
  editorValue, 
  diff, 
  oldCode, 
  newCode, 
  onClearDiff, 
  onSave, 
  sendMessage, 
  validationError, 
  onEditorValueChange,
  isProcessing,
  isDiffPending
}: WorkspaceProps) {
  const [internalValue, setInternalValue] = useState(editorValue);

  // Update internal value when filename or editorValue changes
  useEffect(() => {
    setInternalValue(editorValue);
  }, [editorValue, filename]);

  // Determine if the editor/save actions should be locked
  const isLocked = isProcessing || isDiffPending;

  const handleEditorChange = (value: string) => {
    // Only allow changes if not locked
    if (!isLocked) {
      setInternalValue(value);
      if (onEditorValueChange) onEditorValueChange(value);
    }
  };

  const handleSave = () => {
    if (filename && !isLocked) { // Check lock before saving
      onSave(filename, internalValue);
    }
  };

  const handleDiffAccept = () => {
    if (isProcessing) return; // Don't accept if backend is busy elsewhere
    sendMessage({
      action: 'apply_diff',
      filename,
      diff: diff
    });
    onClearDiff();
  };

  const handleDiffReject = () => {
    if (isProcessing) return; // Don't reject if backend is busy elsewhere
    onClearDiff();
  };

  // Use backend-provided oldCode/newCode for the diff viewer
  const original = oldCode || '';
  const modified = newCode || '';

  return (
    <div className="relative h-full">
      <div className="h-full pb-[120px]">
        {filename && content ? (
          diff ? (
            <div className="h-full flex flex-col">
              <div className="flex justify-between items-center px-4 py-2 border-b border-border">
                <h3 className="text-sm font-medium">Suggested Changes to {filename}</h3>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 gap-1"
                    onClick={handleDiffReject}
                    disabled={isProcessing}
                  >
                    <X className="h-3.5 w-3.5" />
                    Reject
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    className="h-7 gap-1"
                    onClick={handleDiffAccept}
                    disabled={isProcessing}
                  >
                    <Check className="h-3.5 w-3.5" />
                    Accept
                  </Button>
                </div>
              </div>
              {validationError && (
                <div className="bg-destructive/10 border-l-4 border-destructive p-3 text-sm">
                  <h4 className="font-medium text-destructive mb-1">Validation Error</h4>
                  <div className="text-xs whitespace-pre-wrap">{validationError}</div>
                </div>
              )}
              <div className="flex-1 overflow-auto">
                <DiffViewer 
                  original={original} 
                  modified={modified} 
                  language="python" 
                  originalLabel="Current Code"
                  modifiedLabel="Proposed Changes"
                />
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col">
              <div className="flex justify-between items-center px-4 py-2 border-b border-border">
                <h3 className="text-sm font-medium">{filename}</h3>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7"
                  onClick={handleSave}
                  disabled={isLocked}
                >
                  Save
                </Button>
              </div>
              <div className="flex-1">
                <Editor
                  value={internalValue}
                  onChange={handleEditorChange}
                  language="based"
                  options={{ readOnly: isLocked }}
                />
              </div>
            </div>
          )
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
            <p className="mb-4">No file yet. Start by describing your agent idea below.</p>
          </div>
        )}
      </div>
    </div>
  );
}