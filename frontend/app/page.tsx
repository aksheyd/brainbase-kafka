'use client';

import { useEffect, useState, useCallback } from 'react';
import { Workspace } from '@/components/workspace/Workspace';
import { FileExplorer } from '@/components/workspace/FileExplorer';
import { Header } from '@/components/layout/Header';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useToast } from '@/hooks/use-toast';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { PromptPanel } from '@/components/workspace/PromptPanel';
import { ChatPanel } from '@/components/workspace/ChatPanel';

// Type for diff state
type DiffStateType = {
  diff: string | null;
  old_code?: string | null; // Optional, might not always be sent
  new_code?: string | null; // Optional
};

// Type for chat messages (can be expanded)
type ChatMessage = {
  id: string; // For key prop
  role: 'user' | 'agent' | 'system';
  content: string;
};

export default function Home() {
  const [files, setFiles] = useState<string[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [editorValues, setEditorValues] = useState<Record<string, string>>({}); // Tracks editor content per file
  const { toast } = useToast();
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]); // Restore chat state

  const {
    connect,
    sendMessage,
    lastMessage,
    connectionStatus
  } = useWebSocket();

  const [diffStates, setDiffStates] = useState<Record<string, DiffStateType>>({});
  const [validationError, setValidationError] = useState<string | null>(null); // Keep for potential backend errors
  const [isProcessing, setIsProcessing] = useState(false); 

  // Connect WebSocket on mount
  useEffect(() => {
    connect();
  }, [connect]);

  // Removed effect that requested list_files on connect, backend sends initial_state now
  // Removed effect that auto-selected files[0], handled by initial_state and file_created

  // Main message handler
  useEffect(() => {
    if (!lastMessage) return;

    let data;
    try {
        data = JSON.parse(lastMessage);
    } catch (e) {
        console.error("Failed to parse WebSocket message:", lastMessage, e);
        // Wrap toast call in setTimeout
        setTimeout(() => {
            toast({ title: "WebSocket Error", description: "Received invalid message format.", variant: "destructive" });
        }, 0);
        setIsProcessing(false);
        return;
    }

    if (data.status === 'error') {
      setValidationError(data.error); 
      // Wrap toast call in setTimeout
      setTimeout(() => {
          toast({
            title: `Error (${data.action || 'General'})`,
            description: data.error,
            variant: 'destructive',
          });
      }, 0);
      setIsProcessing(false); 
      if (data.action === 'apply_diff_error' && data.filename) {
         setDiffStates(prev => {
           const newStates = { ...prev };
           delete newStates[data.filename];
           return newStates;
         });
      }
      return;
    } else {
      if (validationError) setValidationError(null); 
    }

    // --- Handle Success Messages by Action --- 
    switch (data.action) {
      case 'initial_state':
        setFiles(data.files || []);
        // Don't automatically select a file here, wait for user or file_created
        setActiveFile(null); 
        setEditorValues({}); // Clear editor values on reconnect/initial state
        setDiffStates({}); // Clear diffs
        setChatMessages([]); // Restore chat state update
        setIsProcessing(false);
        break;

      case 'file_list': // Backend confirms file list (e.g., after manual upload/delete)
        setFiles(data.files || []);
        // If active file no longer exists, deactivate it
        if (activeFile && !data.files?.includes(activeFile)) {
          setActiveFile(null);
        }
        break;

      case 'file_content': // Response to read_file request
        if (data.filename && data.filename === activeFile) {
          setEditorValues(prev => ({
            ...prev,
            [data.filename]: data.content ?? '' // Use empty string if content is null/undefined
          }));
          // Clear diff state when explicitly reading/loading file content
          if (diffStates[data.filename]) {
            setDiffStates(prev => {
              const newStates = { ...prev };
              delete newStates[data.filename];
              return newStates;
            });
          }
        }
        break;

      case 'file_created': // AI created a new file
        setFiles(data.files || []); // Update file list from backend
        setActiveFile(data.filename);
        setEditorValues(prev => ({
          ...prev,
          [data.filename]: data.content ?? ''
        }));
        setIsProcessing(false);
        // Optional: Add a system message to chat
        setChatMessages(prev => [...prev, { id: Date.now().toString(), role: 'system', content: `Created file: ${data.filename}` }]); // Restore chat state update
        break;

      case 'diff_generated': // AI generated a diff for the active file
        if (data.filename && data.diff) {
           setDiffStates(prev => ({
             ...prev,
             [data.filename]: {
               diff: data.diff,
               old_code: data.old_code, 
               new_code: data.new_code,
             }
           }));
           // Add system message to chat
           setChatMessages(prev => [...prev, { id: Date.now().toString(), role: 'system', content: `Diff generated for ${data.filename}. Review the changes.` }]);
        }
        setIsProcessing(false);
        break;
        
      case 'diff_applied': // Diff was successfully applied on the backend
        if (data.filename) {
          // Clear diff state is handled first
          setDiffStates(prev => {
            const newStates = { ...prev };
            delete newStates[data.filename]; 
            return newStates;
          });
          // Update editor content
          setEditorValues(prev => ({
            ...prev,
            [data.filename]: data.new_code ?? ''
          }));
          // Add system message to chat
          setChatMessages(prev => [...prev, { id: Date.now().toString(), role: 'system', content: `Changes applied to ${data.filename}.` }]);
           // Toast is deferred
           setTimeout(() => {
                toast({ title: "Diff Applied", description: `Changes applied to ${data.filename}` });
           }, 0);
        }
        break;
        
      case 'file_uploaded': // User manually uploaded/created/saved a file
        setFiles(data.files || []); // Update list from backend
        // No need to setActiveFile or load content here, 
        // handleFileSelect or handleCreateFile already manage the active state/content.
        // Toast notification is handled in handleSaveFile/handleCreateFile
        break;

      // Add cases for backend error actions if needed for specific UI feedback
      case 'edit_error':
      case 'apply_diff_error':
        // Error toast is already handled by the generic error handling block
        setIsProcessing(false);
        break;

      default:
        console.warn("Received unknown WebSocket action:", data.action);
    }
  }, [lastMessage, toast, sendMessage]); 

  // Wrap sendMessage in useCallback to prevent re-renders of child components
  const stableSendMessage = useCallback(sendMessage, [sendMessage]);

  const handleFileSelect = useCallback((filename: string) => {
    if (filename === activeFile || isProcessing) return; // Prevent switching while processing

    const fileToSave = activeFile; 
    const currentContent = fileToSave ? editorValues[fileToSave] : undefined;

    // Clear diff state for the file being left
    if (fileToSave && diffStates[fileToSave]) {
       setDiffStates(prev => {
          const newStates = { ...prev };
          delete newStates[fileToSave!]; 
          return newStates;
       });
    }

    // Auto-save the file being left if its content exists in editorValues (basic check)
    if (fileToSave && currentContent !== undefined) { 
       stableSendMessage({
           action: 'upload_file',
           filename: fileToSave,
           content: currentContent,
       });
       toast({
        title: 'Auto-saved',
        description: `${fileToSave} saved.`,
       });
    }

    // Switch to new file and load its content
    setActiveFile(filename);
    setEditorValues(prev => ({ ...prev, [filename]: prev[filename] ?? "Loading..." })); // Show loading indicator
    stableSendMessage({ action: 'read_file', filename });
  }, [activeFile, isProcessing, editorValues, diffStates, stableSendMessage, toast]);

  // Handles prompt submission from PromptPanel
  const handlePromptSubmit = useCallback((prompt: string) => {
    if (!prompt.trim() || isProcessing) return;

    setIsProcessing(true);
    setValidationError(null); 
    // Add user prompt to chat display
    setChatMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', content: prompt }]); // Restore chat state update

    stableSendMessage({
      action: 'prompt',
      prompt: prompt.trim(),
      activeFile: activeFile, 
    });
  }, [isProcessing, activeFile, stableSendMessage]);

 // For manual file creation (e.g., File > New or explorer button)
 const handleCreateFile = useCallback((filename: string) => {
    if (isProcessing) return; // Prevent creation while processing
    let newFilename = filename.trim();
    if (!newFilename) {
        toast({ title: "Invalid Name", description: "Filename cannot be empty.", variant: "destructive" });
        return;
    }
    if (!newFilename.endsWith('.based')) {
      newFilename = `${newFilename}.based`;
    }
    if (files.includes(newFilename)) {
      toast({ title: "File Exists", description: `'${newFilename}' already exists.`, variant: "destructive" });
      return;
    }

    // Optimistically update UI
    setFiles(prev => [...prev, newFilename]);
    setActiveFile(newFilename);
    setEditorValues(prev => ({ ...prev, [newFilename]: '' })); // Set empty content
    setDiffStates(prev => {
        const newStates = { ...prev };
        delete newStates[newFilename]; // Ensure no old diff state persists
        return newStates;
    });

    // Tell backend to create the empty file
    stableSendMessage({
      action: 'upload_file',
      filename: newFilename,
      content: '' 
    });
    toast({ title: "File Created", description: `'${newFilename}' created.` });
  }, [files, isProcessing, stableSendMessage, toast]);

  // For handling editor changes directly (updates local state)
  const handleEditorChange = useCallback((filename: string, content: string) => {
      setEditorValues(prev => ({
          ...prev,
          [filename]: content
      }));
      // If user edits a file with a pending diff, clear the diff
      if (diffStates[filename]) {
          setDiffStates(prev => {
              const newStates = { ...prev };
              delete newStates[filename];
              return newStates;
          });
          toast({ title: "Diff Cleared", description: "Manual edits cleared the pending AI diff.", variant: "default" });
      }
  }, [diffStates, toast]);

  // For explicitly saving the current file (e.g., Ctrl+S or button)
  const handleSaveFile = useCallback(() => {
    if (!activeFile || isProcessing) return;
    const contentToSave = editorValues[activeFile];
    if (contentToSave === undefined) {
      // This shouldn't happen if a file is active, but defensively check
      console.warn("Attempted to save file with no content loaded:", activeFile);
      return;
    }

    stableSendMessage({
      action: 'upload_file',
      filename: activeFile,
      content: contentToSave
    });

    toast({ title: "File Saved", description: `'${activeFile}' saved.` });

    // Clear diff state on explicit save
    if (diffStates[activeFile]) {
        setDiffStates(prev => {
            const newStates = { ...prev };
            delete newStates[activeFile!];
            return newStates;
        });
    }
  }, [activeFile, isProcessing, editorValues, diffStates, stableSendMessage, toast]);

  // For applying a diff shown in the UI
  const handleApplyDiff = useCallback((filename: string) => {
    if (!diffStates[filename]?.diff || isProcessing) return;

    // Add system message before sending request
    setChatMessages(prev => [...prev, { id: Date.now().toString(), role: 'system', content: `Applying changes to ${filename}...` }]);
    setIsProcessing(true); // Indicate processing for diff application
    stableSendMessage({
      action: 'apply_diff',
      filename: filename,
      diff: diffStates[filename]!.diff!
    });
  }, [diffStates, isProcessing, stableSendMessage]);

  // Function to clear diff state for a given file
  const handleClearDiff = useCallback((filename: string) => {
      setDiffStates(prev => {
          const newStates = { ...prev };
          if (newStates[filename]) {
              delete newStates[filename];
              // Wrap toast in setTimeout
              setTimeout(() => {
                 toast({ title: "Diff Cleared", description: `Changes for ${filename} discarded.` });
              }, 0);
          }
          return newStates;
      });
  }, [toast]);

  // Determine if the UI should be locked
  const isDiffPending = !!(activeFile && diffStates[activeFile]);
  const isUiLocked = isProcessing || isDiffPending;

  // Determine current content to display (editor value or original if diff exists)
  const currentFileContent = activeFile ? (diffStates[activeFile]?.old_code ?? editorValues[activeFile] ?? '') : '';
  const currentDiff = activeFile ? diffStates[activeFile]?.diff : null;

  return (
    <div className="flex flex-col h-screen">
      <Header connectionStatus={connectionStatus} />
      {/* Outer horizontal group: Explorer | Workspace | Chat */}
      <ResizablePanelGroup direction="horizontal" className="flex-1 border-t">
        {/* Left Panel: File Explorer */}
        <ResizablePanel defaultSize={20} minSize={15} maxSize={30}>
          <FileExplorer
            files={files}
            activeFile={activeFile}
            onSelectFile={handleFileSelect}
            isLocked={isUiLocked}
          />
        </ResizablePanel>
        <ResizableHandle withHandle />
        
        {/* Middle Panel: Workspace ONLY */}
        <ResizablePanel defaultSize={80} minSize={30}> {/* Adjusted size */}
              <Workspace
                filename={activeFile}
                content={currentFileContent} 
                diff={currentDiff} 
                editorValue={activeFile ? editorValues[activeFile] ?? '' : ''}
                oldCode={activeFile ? diffStates[activeFile]?.old_code : null}
                newCode={activeFile ? diffStates[activeFile]?.new_code : null}
                onEditorValueChange={(newContent) => {
                  if (activeFile) { handleEditorChange(activeFile, newContent); }
                }}
                onSave={() => { if(activeFile) handleSaveFile(); }}
                sendMessage={stableSendMessage} 
                onClearDiff={() => { if(activeFile) handleClearDiff(activeFile); }}
                validationError={validationError} 
                isProcessing={isProcessing} 
                isDiffPending={isDiffPending}
              />
        </ResizablePanel>
        <ResizableHandle withHandle />

        {/* Right Panel: Chat History - Commented out */}
        <ResizablePanel defaultSize={25} minSize={20}>
            <ChatPanel chatMessages={chatMessages} />
        </ResizablePanel>

      </ResizablePanelGroup>

       {/* PromptPanel: Fixed position */}
       <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 w-full max-w-3xl px-4 z-50">
          <PromptPanel
            onSubmit={handlePromptSubmit}
            isLocked={isUiLocked}
          />
       </div>

    </div>
  );
}