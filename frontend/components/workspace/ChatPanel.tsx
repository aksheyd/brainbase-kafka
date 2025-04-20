'use client';

import { useRef, useEffect } from 'react';
import { cn } from "@/lib/utils";
import { User, Bot } from 'lucide-react';

// Type for chat messages (copied from page.tsx)
type ChatMessage = {
  id: string; 
  role: 'user' | 'agent' | 'system';
  content: string;
};

type ChatPanelProps = {
  chatMessages: ChatMessage[];
};

export function ChatPanel({ chatMessages }: ChatPanelProps) {
  // Removed scrollAreaRef 
  // const scrollAreaRef = useRef<HTMLDivElement>(null); 

  // Auto-scroll logic is already removed

  return (
    <div className="h-full flex flex-col bg-background border-l border-border">
       <div className="p-4 border-b border-border">
          <h3 className="text-lg font-semibold">Conversation</h3>
       </div>
      <div className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-4">
          {chatMessages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex items-start gap-3 p-3 rounded-lg max-w-[90%]",
                message.role === 'user' 
                    ? "bg-primary/10 ml-auto" 
                    : message.role === 'system' 
                        ? "bg-amber-400/10 mx-auto text-xs text-amber-600 border border-amber-400/30" // System message style
                        : "bg-muted/50 mr-auto" // Agent message style
              )}
            >
              {message.role === 'user' && <User className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />}
              {message.role === 'agent' && <Bot className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />}
              {/* No icon for system messages, or add one if desired */} 
              <p className={cn(
                 "text-sm whitespace-pre-wrap break-words",
                 message.role === 'system' ? "italic" : ""
              )}>
                 {message.content}
               </p>
            </div>
          ))}
           {chatMessages.length === 0 && (
             <div className="text-center text-sm text-muted-foreground py-8">
               Conversation history will appear here.
             </div>
           )} 
        </div>
      </div>
    </div>
  );
} 