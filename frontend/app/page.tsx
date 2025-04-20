'use client';

import { useEffect, useState } from 'react';
import { Workspace } from '@/components/workspace/Workspace';
import { FileExplorer } from '@/components/workspace/FileExplorer';
import { Header } from '@/components/layout/Header';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useToast } from '@/hooks/use-toast';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { PromptPanel } from '@/components/workspace/PromptPanel';

// Type for diff state
type DiffStateType = {
  diff: string | null;
  old_code: string | null;
  new_code: string | null;
};

export default function Home() {
  // Simplified state - only what the UI needs
  const [files, setFiles] = useState<string[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [editorValues, setEditorValues] = useState<Record<string, string>>({}); // Tracks unsaved editor content
  const { toast } = useToast();

  const {
    connect,
    sendMessage,
    lastMessage,
    connectionStatus
  } = useWebSocket();

  // File-specific diff states
  const [diffStates, setDiffStates] = useState<Record<string, DiffStateType>>({});

  const [validationError, setValidationError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false); // State to track AI processing

  useEffect(() => {
    connect();
  }, [connect]);

  useEffect(() => {
    if (connectionStatus === 'connected') {
      // Always fetch the current file list from backend
      sendMessage({ action: 'list_files' });
    }
  }, [connectionStatus, sendMessage]);

  // When the file list changes and we don't have an active file yet,
  // automatically select the first file (which should be agent.based)
  useEffect(() => {
    if (files.length > 0 && !activeFile) {
      const firstFile = files[0];
      setActiveFile(firstFile);
      sendMessage({ action: 'read_file', filename: firstFile });
    }
  }, [files, activeFile, sendMessage]); // Depend on files and activeFile

  useEffect(() => {
    if (!lastMessage) return;

    const data = JSON.parse(lastMessage);

    if (data.status === 'error') {
      // Handle specific errors differently if needed
      if (data.action === 'apply_diff') {
        toast({
          title: 'Diff Apply Failed',
          description: data.error,
          variant: 'destructive',
        });
        // Optionally clear the diff state for the file on error
        if (data.filename) {
           setDiffStates(prev => {
             const newStates = { ...prev };
             delete newStates[data.filename];
             return newStates;
           });
        }
      } else {
        setValidationError(data.error);
        toast({
          title: 'Error',
          description: data.error,
          variant: 'destructive',
        });
      }
      setIsProcessing(false); // Stop processing on any error
      return;
    } else if (validationError !== null) {
      // Clear general validation error on any success
      setValidationError(null);
    }

    switch (data.action) {
      case 'list_files':
        setFiles(data.files);
        break;
      case 'read_file':
        // Update editor value only for the active file being read
        if (data.filename === activeFile) {
          setEditorValues(prev => ({
            ...prev,
            [data.filename]: data.content
          }));
          // Ensure diff state is cleared if we re-read a file that had a diff
          if (diffStates[data.filename]) {
            setDiffStates(prev => {
              const newStates = { ...prev };
              delete newStates[data.filename];
              return newStates;
            });
          }
        }
        break;
      case 'prompt':
        setIsProcessing(false); // Stop processing after prompt response
        if (data.code) {
          const filename = data.filename || activeFile || 'agent.based';
          setEditorValues(prev => ({
            ...prev,
            [filename]: data.code
          }));

          // Refresh file list to make sure UI is in sync with backend
          sendMessage({ action: 'list_files' });

          if (!activeFile) {
            setActiveFile(filename);
          }
        }
        break;
      case 'generate_diff':
        setIsProcessing(false); // Stop processing after diff response
        // Diff generated for a specific file (use activeFile as fallback)
        const diffFilename = data.filename || activeFile;
        if (diffFilename && data.diff) {
           setDiffStates(prev => ({
             ...prev,
             [diffFilename]: {
               diff: data.diff,
               old_code: data.old_code || '',
               new_code: data.new_code || '',
             }
           }));
        }
        break;
      case 'apply_diff':
        // Diff applied successfully on backend for data.filename
        setDiffStates(prev => {
          const newStates = { ...prev };
          delete newStates[data.filename]; // Clear diff for this file
          return newStates;
        });
        // Update editor content with the new code from backend
        setEditorValues(prev => ({
          ...prev,
          [data.filename]: data.new_code
        }));
        break;
      case 'upload_file':
        // File was successfully created or updated on the backend.
        // Refresh the file list to ensure UI consistency.
        sendMessage({ action: 'list_files' });
        // If this upload corresponds to the currently active file (likely just created),
        // immediately fetch its content.
        if (data.filename === activeFile) {
          sendMessage({ action: 'read_file', filename: data.filename });
        }
        break;
    }
  }, [lastMessage, toast, activeFile, sendMessage]); // Added diffStates dependency

  const handleFileSelect = (filename: string) => {
    if (filename === activeFile) return;

    const fileToSave = activeFile; // Store the file we are leaving
    const currentContent = fileToSave ? editorValues[fileToSave] : undefined;

    // Clear diff state for the file being left, if any
    if (fileToSave && diffStates[fileToSave]) {
       setDiffStates(prev => {
          const newStates = { ...prev };
          delete newStates[fileToSave!]; 
          return newStates;
       });
    }

    // Save current file's content ONLY if it was edited
    // Simple check: does editorValues have an entry for this file?
    // A more robust check would compare against the last known saved state.
    if (fileToSave && currentContent !== undefined) { 
       sendMessage({
           action: 'upload_file',
           filename: fileToSave,
           content: currentContent,
       });
       // Auto-save toast
       toast({
        title: 'File saved',
        description: `${fileToSave} has been saved.`,
       });
    }

    // Switch to new file and load its content
    setActiveFile(filename);
    sendMessage({ action: 'read_file', filename });
  };

 const handleCreateFile = (filename: string) => {
    if (!filename.endsWith('.based')) {
      filename = `${filename}.based`;
    }
    const newFilename = filename; // Use a constant for clarity

    // Optimistically add the file to the frontend list
    if (!files.includes(newFilename)) {
      setFiles(prev => [...prev, newFilename]);
    }

    // Set the new file as active 
    setActiveFile(newFilename);
    setEditorValues(prev => ({ ...prev, [newFilename]: '' })); // Set empty content locally

    // Create empty file on backend
    sendMessage({
      action: 'upload_file',
      filename: newFilename,
      content: '' 
    });
    // The backend confirmation will refresh the list, solidifying the state
  };

  const handleSaveFile = (filename: string, content: string) => {
    // Update backend with the latest content
    sendMessage({
      action: 'upload_file',
      filename,
      content
    });

    // Update local editor state
    setEditorValues(prev => ({
      ...prev,
      [filename]: content
    }));
    
    // Clear diff state for this file if it existed
    if (diffStates[filename]) {
        setDiffStates(prev => {
          const newStates = { ...prev };
          delete newStates[filename];
          return newStates;
        });
    }

    toast({
      title: 'File saved',
      description: `${filename} has been saved.`,
     });
  };

  return (
    <main className="flex flex-col h-screen bg-background">
      <Header connectionStatus={connectionStatus} />

      <ResizablePanelGroup
        direction="horizontal"
        className="flex-1 h-[calc(100vh-3.5rem)]"
      >
        <ResizablePanel
          defaultSize={20}
          minSize={15}
          maxSize={30}
          className="border-r border-border"
        >
          <FileExplorer
            files={files}
            activeFile={activeFile}
            onSelectFile={handleFileSelect}
            onCreateFile={handleCreateFile}
          />
        </ResizablePanel>

        <ResizableHandle />

        <ResizablePanel defaultSize={80}>
          {activeFile ? (
            <Workspace
              filename={activeFile}
              content={editorValues[activeFile] || ''} // Base content for rendering logic
              editorValue={editorValues[activeFile] || ''} // Value shown in editor
              diff={diffStates[activeFile]?.diff || null} // Pass diff for the active file
              oldCode={diffStates[activeFile]?.old_code || null} // Pass oldCode for the active file
              newCode={diffStates[activeFile]?.new_code || null} // Pass newCode for the active file
              onClearDiff={() => { // Clear diff for the *active* file
                setDiffStates(prev => {
                  const newStates = { ...prev };
                  if (activeFile) delete newStates[activeFile];
                  return newStates;
                });
              }}
              onSave={handleSaveFile}
              sendMessage={sendMessage}
              validationError={validationError}
              onEditorValueChange={val => {
                if (activeFile) {
                  setEditorValues(prev => ({ ...prev, [activeFile]: val }));
                }
              }}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Select a file or create a new one to get started.
            </div>
          )}
        </ResizablePanel>
      </ResizablePanelGroup>

      {/* Always render PromptPanel, fixed at the bottom */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[600px] max-w-[calc(100vw-2rem)] z-50">
        <PromptPanel
          isProcessing={isProcessing}
          onSubmit={(prompt, context) => {
            const currentActiveFile = activeFile || 'agent.based'; // Ensure we have a filename
            const maybeContext = context ? { context } : {};

            // Determine if the active file is empty or not
            const isActiveFileEmpty = !editorValues[currentActiveFile] || editorValues[currentActiveFile].trim() === '';

            setIsProcessing(true); // Start processing before sending message
            if (isActiveFileEmpty) {
              // If file is empty, treat as initial prompt for that file
              sendMessage({
                action: 'prompt',
                prompt,
                filename: currentActiveFile,
                ...maybeContext,
              });
              // Ensure the file becomes active if it wasn't (e.g., first prompt)
              if (!activeFile) setActiveFile(currentActiveFile);
            } else {
              // If file has content, generate a diff
              sendMessage({
                action: 'generate_diff',
                prompt,
                filename: currentActiveFile, // Explicitly send filename for diff
                current_code: editorValues[currentActiveFile],
                ...maybeContext,
              });
            }
          }}
        />
      </div>
    </main>
  );
}