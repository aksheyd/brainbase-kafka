'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Menu, Code, Github, Brain, GitBranch, Wifi, WifiOff, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

/** Defines the possible states of the WebSocket connection. */
type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

interface HeaderProps {
  /** The current status of the WebSocket connection. */
  connectionStatus: ConnectionStatus;
  /** Whether an AI operation (like generating code/diff) is in progress. */
  isProcessing: boolean;
  /** Whether a diff has been generated and is awaiting user review. */
  isDiffPending: boolean;
}

/**
 * The main application header component.
 * Displays branding, navigation (stubbed), connection status, activity status, and authentication actions.
 */
export function Header({ connectionStatus, isProcessing, isDiffPending }: HeaderProps) {
  /** Determines the Tailwind classes for the connection status indicator based on the status. */
  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-green-500/10 text-green-400'; 
      case 'connecting':
        return 'bg-yellow-500/10 text-yellow-400'; 
      case 'disconnected':
        return 'bg-red-500/10 text-red-400'; 
    }
  };

  // Determine the appropriate icon and text based on connection status
  const StatusIcon = connectionStatus === 'connected' ? Wifi : connectionStatus === 'connecting' ? Loader2 : WifiOff;
  const statusText = connectionStatus === 'connected' ? 'Connected' : connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected';

  // Determine the text to display for the current activity status
  let activityStatus = '';
  if (isProcessing) {
    activityStatus = 'Processing (Editor locked)...'; 
  } else if (isDiffPending) {
    activityStatus = 'Review pending changes'; 
  }

  return (
    <header className="flex h-14 items-center border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4">
      {/* Branding Section */}
      <div className="flex items-center gap-2 mr-4">
        <Brain className="w-6 h-6 text-primary" />
        <span className="font-semibold text-lg">Kafka</span>
      </div>
      
      {/* Desktop Navigation (Placeholder) */}
      <nav className="hidden md:flex items-center space-x-4 lg:space-x-6 mx-6">
        {/* These buttons currently don't have functionality */}
        <Button variant="ghost" size="sm" className="h-8 px-2">
          File
        </Button>
        <Button variant="ghost" size="sm" className="h-8 px-2">
          Edit
        </Button>
        <Button variant="ghost" size="sm" className="h-8 px-2">
          View
        </Button>
        <Button variant="ghost" size="sm" className="h-8 px-2">
          Help
        </Button>
      </nav>
      
      {/* Right Section (Desktop) */}
      <div className="hidden md:flex items-center ml-auto gap-2">
        {/* Activity Status Indicator */}
        {activityStatus && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> {/* Spinning loader */}
            <span>{activityStatus}</span>
          </div>
        )}
        
        {/* Connection Status Indicator */}
        <div className={cn(
          "flex items-center gap-2 text-xs px-3 py-1 rounded-full",
          getStatusColor() // Apply dynamic background/text color
        )}>
          {/* Status dot */}
          <div className={cn(
            "w-2 h-2 rounded-full",
            connectionStatus === 'connected' ? "bg-green-400" : 
            connectionStatus === 'connecting' ? "bg-yellow-400" : 
            "bg-red-400"
          )} />
          {/* Status text */}
          {statusText}
        </div>
        
        {/* Language Indicator (Placeholder) */}
        <Button variant="outline" size="sm" className="gap-1">
          <Code className="h-4 w-4 mr-1" />
          .based
        </Button>
        
        {/* Sign In Button (Placeholder) */}
        <Button size="sm" variant="default">
          <Github className="h-4 w-4 mr-2" />
          Sign In
        </Button>
      </div>
    </header>
  );
}