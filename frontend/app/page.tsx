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
import { DiffState, ChatMessage } from '@/lib/types';


/**
 * The main page component for the Kafka application.
 * Manages application state, WebSocket communication, and renders the UI layout.
 */
export default function Home() {
  // Workspace and UI state
  const [files, setFiles] = useState<string[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [editorValues, setEditorValues] = useState<Record<string, string>>({});
  const { toast } = useToast();
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  // WebSocket connection and message state
  const {
    connect,
    sendMessage,
    lastMessage,
    connectionStatus
  } = useWebSocket();

  // Diff, error, and processing state
  const [diffStates, setDiffStates] = useState<Record<string, DiffState>>({});
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Connect WebSocket on mount
  useEffect(() => {
    connect();
  }, [connect]);

  // Handle incoming WebSocket messages and update state accordingly
  useEffect(() => {
    if (!lastMessage) return;

    let data : any;
    try {
      // Attempt to parse the incoming message as JSON
      data = JSON.parse(lastMessage);
    } catch (e) {
      // Handle JSON parsing errors
      console.error("Failed to parse WebSocket message:", lastMessage, e);
      // Show an error toast (wrapped in setTimeout to avoid issues during render)
      setTimeout(() => {
        toast({ title: "WebSocket Error", description: "Received invalid message format.", variant: "destructive" });
      }, 0);
      setIsProcessing(false); // Ensure processing state is reset
      return; // Stop further processing of this message
    }

    // --- Handle Backend Errors ---
    if (data.status === 'error') {
      setValidationError(data.error); // Store the error message
      // Show a generic error toast (wrapped in setTimeout)
      setTimeout(() => {
        toast({
          title: `Error (${data.action || 'General'})`, // Include action if available
          description: data.error,
          variant: 'destructive',
        });
      }, 0);
      setIsProcessing(false); // Reset processing state
      // If the error was related to applying a diff, clear the diff state for that file
      if (data.action === 'apply_diff_error' && data.filename) {
        setDiffStates(prev => {
          const newStates = { ...prev };
          delete newStates[data.filename]; // Remove the failed diff
          return newStates;
        });
      }
      return; // Stop further processing
    } else {
      // Clear any previous validation error if the current message is successful
      if (validationError) setValidationError(null);
    }

    // --- Handle Success Messages by Action --- 
    switch (data.action) {
      case 'initial_state':
        // Received initial state from backend upon connection
        setFiles(data.files || []); // Update file list
        setActiveFile(null); // Start with no active file
        setEditorValues({}); // Clear any stale editor content
        setDiffStates({}); // Clear any stale diffs
        setChatMessages([]); // Clear chat history
        setIsProcessing(false); // Ensure processing state is reset
        break;

      case 'file_list':
        // Backend confirmed an updated file list (e.g., after manual actions not covered here)
        setFiles(data.files || []);
        // If the currently active file was deleted, deactivate it
        if (activeFile && !data.files?.includes(activeFile)) {
          setActiveFile(null);
        }
        break;

      case 'file_content':
        // Received content for a file requested via 'read_file'
        if (data.filename && data.filename === activeFile) {
          // Update the editor value for the active file
          setEditorValues(prev => ({
            ...prev,
            [data.filename]: data.content ?? '' // Use empty string if content is missing
          }));
          // Clear any pending diff for this file, as we just loaded fresh content
          if (diffStates[data.filename]) {
            setDiffStates(prev => {
              const newStates = { ...prev };
              delete newStates[data.filename];
              return newStates;
            });
          }
        }
        break;

      case 'file_created':
        // AI successfully created a new file
        setFiles(data.files || []); // Update file list from backend response
        setActiveFile(data.filename); // Make the new file active
        // Set the initial content for the new file in the editor
        setEditorValues(prev => ({
          ...prev,
          [data.filename]: data.content ?? ''
        }));
        setIsProcessing(false); // Mark processing as complete
        // Add a system message to the chat
        setChatMessages(prev => [...prev, { id: crypto.randomUUID(), role: 'system', content: `Created file: ${data.filename}` }]);
        break;

      case 'diff_generated':
        // AI generated a diff for the active file
        if (data.filename && data.diff) {
          // Store the diff details (diff string, old/new code)
          setDiffStates(prev => ({
            ...prev,
            [data.filename]: {
              diff: data.diff,
              old_code: data.old_code,
              new_code: data.new_code,
            }
          }));
          // Add a system message prompting the user to review
          setChatMessages(prev => [...prev, { id: crypto.randomUUID(), role: 'system', content: `Diff generated for ${data.filename}. Review the changes.` }]);
        }
        setIsProcessing(false); // Mark processing as complete
        break;

      case 'diff_applied':
        // Backend successfully applied a diff
        if (data.filename) {
          // 1. Clear the diff state for the file
          setDiffStates(prev => {
            const newStates = { ...prev };
            delete newStates[data.filename];
            return newStates;
          });
          // 2. Update the editor content with the new code from the backend
          setEditorValues(prev => ({
            ...prev,
            [data.filename]: data.new_code ?? ''
          }));
          // 3. Add a system message to the chat
          setChatMessages(prev => [...prev, { id: crypto.randomUUID(), role: 'system', content: `Changes applied to ${data.filename}.` }]);
          // 4. Show a success toast (deferred)
          setTimeout(() => {
            toast({ title: "Diff Applied", description: `Changes applied to ${data.filename}` });
          }, 0);
          // Note: isProcessing should be reset *after* applying the diff, handled implicitly if no further actions
        }
        // Assuming diff application finishes processing here
        setIsProcessing(false);
        break;

      case 'file_uploaded':
        // User manually saved/created a file, backend confirms list update
        setFiles(data.files || []); // Update file list
        // Toast notification is also handled there.
        break;

      // Specific error actions (optional, as generic error handling exists)
      case 'edit_error':
      case 'apply_diff_error':
        setIsProcessing(false); // Ensure processing stops on error
        break;

      default:
        // Log unexpected actions from the backend
        console.warn("Received unknown WebSocket action:", data.action);
        setIsProcessing(false);
    }
  }, [lastMessage, toast, sendMessage]);

  // Memoized sendMessage for child components
  const stableSendMessage = useCallback(sendMessage, [sendMessage]);

  // File selection handler: auto-saves current file before switching
  const handleFileSelect = useCallback((filename: string) => {
    // Prevent switching if the same file is clicked or if processing a diff
    if (filename === activeFile || isProcessing) return;

    const fileToLeave = activeFile; // File currently being viewed
    const contentToSave = fileToLeave ? editorValues[fileToLeave] : undefined;

    // Auto-save the file being left if it has content loaded in the editor
    if (fileToLeave && contentToSave !== undefined) {
      stableSendMessage({
        action: 'upload_file',
        filename: fileToLeave,
        content: contentToSave,
      });

      // Show auto-save toast
      toast({
        title: 'Auto-saved',
        description: `${fileToLeave} saved.`,
      });
    }

    // Switch to the newly selected file
    setActiveFile(filename);
    // Set editor value to "Loading..." or existing content if already loaded
    setEditorValues(prev => ({ ...prev, [filename]: prev[filename] ?? "Loading..." }));
    // Request the content of the newly selected file from the backend
    stableSendMessage({ action: 'read_file', filename });
  }, [activeFile, isProcessing, editorValues, stableSendMessage, toast]);

  // Prompt submission handler: sends prompt and context to backend
  const handlePromptSubmit = useCallback((prompt: string, context?: string) => {
    // Prevent submission if prompt is empty or processing
    if (!prompt.trim() || isProcessing) return;

    setIsProcessing(true); // Set processing state
    setValidationError(null); // Clear previous errors

    // Add user's prompt to the chat display
    setChatMessages(prev => [...prev, { id: crypto.randomUUID(), role: 'user', content: prompt }]);
    // If context was provided (e.g., from "Add Context" button), add it as a system message
    if (context) {
      setChatMessages(prev => [...prev, { id: crypto.randomUUID(), role: 'agent', content: `Context provided: ${context}` }]);
    }

    // Send the prompt to the backend
    stableSendMessage({
      action: 'prompt',
      prompt: prompt.trim(),
      activeFile: activeFile,
      context,
    });
  }, [isProcessing, activeFile, stableSendMessage]);

  /** Handles changes made directly within the Monaco editor. */
  const handleEditorChange = useCallback((filename: string, content: string) => {
    // Update the local editor state for the specific file
    setEditorValues(prev => ({
      ...prev,
      [filename]: content
    }));
  }, [diffStates, toast]);

  /** Handles explicitly saving the currently active file (e.g., Save button). */
  const handleSaveFile = useCallback(() => {
    // Prevent saving if no file is active or if processing
    if (!activeFile || isProcessing) return;

    const contentToSave = editorValues[activeFile];
    // Defensive check: ensure content is actually loaded before saving
    if (contentToSave === undefined) {
      console.warn("Attempted to save file with no content loaded:", activeFile);
      return;
    }

    // Send the content to the backend to be saved
    stableSendMessage({
      action: 'upload_file',
      filename: activeFile,
      content: contentToSave
    });

    // Show success toast
    toast({ title: "File Saved", description: `'${activeFile}' saved.` });

  }, [activeFile, isProcessing, editorValues, diffStates, stableSendMessage, toast]);


  const handleClearDiff = useCallback((filename: string) => {
    setDiffStates(prev => {
      const newStates = { ...prev };
      // If a diff exists for the file, remove it
      if (newStates[filename]) {
        delete newStates[filename];
        // Show a toast confirming the discard action (deferred)
        setTimeout(() => {
          toast({ title: "Diff Cleared", description: `Changes for ${filename} discarded.` });
        }, 0);
      }
      return newStates; // Return the updated state
    });
  }, [toast]);

  // UI lock state: disables actions when processing or diff is pending
  const isDiffPending = !!(activeFile && diffStates[activeFile]);
  const isUiLocked = isProcessing || isDiffPending;

  // Current file content and diff for editor
  const currentFileContent = activeFile ? (diffStates[activeFile]?.old_code ?? editorValues[activeFile] ?? '') : '';
  const currentDiff = activeFile ? diffStates[activeFile]?.diff : null;

  // --- Render ---
  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      {/* Application Header */}
      <Header
        connectionStatus={connectionStatus}
        isProcessing={isProcessing}
        isDiffPending={isDiffPending} // Pass diff pending state to header
      />

      {/* Main Content Area (Resizable Panels) */}
      <ResizablePanelGroup direction="horizontal" className="flex-1 border-t">

        {/* Left Panel: File Explorer */}
        <ResizablePanel defaultSize={20} minSize={15} maxSize={30}>
          <FileExplorer
            files={files}
            activeFile={activeFile}
            onSelectFile={handleFileSelect} // Pass selection handler
            isLocked={isUiLocked} // Lock explorer during processing/diff review
          />
        </ResizablePanel>
        <ResizableHandle withHandle />

        {/* Middle Panel: Editor/Diff Workspace */}
        <ResizablePanel defaultSize={55} minSize={30}> {/* Adjusted default size */}
          <Workspace
            filename={activeFile}
            content={currentFileContent} // Content to display (original if diff pending)
            diff={currentDiff} // Pass the diff string if it exists
            editorValue={activeFile ? editorValues[activeFile] ?? '' : ''} // Current raw editor value
            oldCode={activeFile ? diffStates[activeFile]?.old_code : null} // Pass old code for diff viewer
            newCode={activeFile ? diffStates[activeFile]?.new_code : null} // Pass new code for diff viewer
            onEditorValueChange={(newContent) => {
              // Update editor state on change
              if (activeFile) { handleEditorChange(activeFile, newContent); }
            }}
            onSave={() => {
              // Trigger save action
              if (activeFile) handleSaveFile();
            }}
            sendMessage={stableSendMessage} // Pass WebSocket send function
            onClearDiff={() => {
              // Trigger diff clear action
              if (activeFile) handleClearDiff(activeFile);
            }}
            validationError={validationError} // Pass validation errors
            isProcessing={isProcessing} // Pass processing state
            isDiffPending={isDiffPending} // Pass diff pending state
          />
        </ResizablePanel>
        <ResizableHandle withHandle />

        {/* Right Panel: Chat History */}
        <ResizablePanel defaultSize={25} minSize={20}>
          <ChatPanel chatMessages={chatMessages} /> {/* Display chat messages */}
        </ResizablePanel>

      </ResizablePanelGroup>

      {/* Prompt Input Panel: Fixed at the bottom */}
      <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 w-full max-w-3xl px-4 z-50">
        <PromptPanel
          onSubmit={handlePromptSubmit} // Pass prompt submission handler
          isLocked={isUiLocked} // Lock prompt input during processing/diff review
        />
      </div>
    </div>
  );
}