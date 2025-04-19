'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Send, HelpCircle, Plus, Loader2 } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { HelpModal } from './HelpModal';

// Sleek shadcn-style input for the main prompt
interface SleekInputProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  inputRef: React.RefObject<HTMLInputElement>;
  placeholder: string;
}

function SleekInput({ value, onChange, onKeyDown, inputRef, placeholder }: SleekInputProps) {
  return (
    <Input
      ref={inputRef}
      value={value}
      onChange={onChange}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
      className="rounded-full px-5 py-2 text-base shadow-sm border border-input bg-background focus:ring-2 focus:ring-ring focus:outline-none transition-all"
    />
  );
}

type PromptPanelProps = {
  onSubmit: (prompt: string, context?: string) => void;
  isProcessing?: boolean;
};

export function PromptPanel({ onSubmit, isProcessing = false }: PromptPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const [showContext, setShowContext] = useState(false);
  const [contextValue, setContextValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const handleSubmit = () => {
    if (!inputValue.trim() || isProcessing) return;
    
    onSubmit(inputValue, showContext ? contextValue : undefined);
    
    // Clear inputs after submission
    setInputValue('');
    setContextValue('');
    setShowContext(false);
    
    // Refocus the input field
    setTimeout(() => {
      if (inputRef.current && !isProcessing) inputRef.current.focus();
    }, 0);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 rounded-2xl border border-border shadow-xl px-6 pt-4 pb-5 flex flex-col gap-3">
      {/* Main input */}
      <Input
        ref={inputRef}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={isProcessing ? "AI is thinking..." : "Ask a question, make a change, go wild..."}
        className="rounded-full px-5 py-2 text-base shadow-sm border border-input focus:ring-2 focus:ring-ring focus:outline-none transition-all"
        disabled={isProcessing}
      />
      
      {/* Context area (optional) */}
      {showContext && (
        <Textarea
          value={contextValue}
          onChange={e => setContextValue(e.target.value)}
          placeholder="Add context for your prompt (optional)"
          className="mt-2 rounded-md border border-input min-h-[60px] max-h-[120px] text-sm"
          disabled={isProcessing}
        />
      )}
      
      {/* Controls */}
      <div className="flex items-end justify-between mt-1">
        <div className="flex items-center gap-2">
          <TooltipProvider>
            {/* <Tooltip>
              <TooltipTrigger asChild> */}
                <Button
                  variant="ghost"
                  size="sm"
                  className="flex items-center gap-1 px-2"
                  onClick={() => setShowContext(v => !v)}
                  disabled={isProcessing}
                >
                  <Plus className="h-4 w-4" />
                  {showContext ? 'Hide context' : 'Add context'}
                </Button>
              {/* </TooltipTrigger>
              <TooltipContent>Add extra context to guide the AI</TooltipContent>
            </Tooltip> */}

            <Tooltip>
              <TooltipTrigger asChild>
                <HelpModal>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="flex items-center gap-1 px-2"
                    disabled={isProcessing}
                  >
                    <HelpCircle className="h-4 w-4" />
                    Help
                  </Button>
                </HelpModal>
              </TooltipTrigger>
              <TooltipContent>How to use Kafka</TooltipContent>
            </Tooltip>

          </TooltipProvider>
        </div>
        
        <Button
          variant="default"
          size="lg"
          className="flex items-center gap-2 px-6 rounded-full"
          onClick={handleSubmit}
          disabled={!inputValue.trim() || isProcessing}
        >
          {isProcessing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              Send
              <Send className="h-4 w-4" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}