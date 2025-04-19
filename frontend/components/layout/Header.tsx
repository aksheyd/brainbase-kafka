'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Menu, Code, Github, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';

type HeaderProps = {
  connectionStatus: 'connecting' | 'connected' | 'disconnected';
};

export function Header({ connectionStatus }: HeaderProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="flex h-14 items-center border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4">
      <div className="flex items-center gap-2 mr-4">
        <Brain className="w-6 h-6 text-primary" />
        <span className="font-semibold text-lg">Kafka</span>
      </div>
      
      <nav className="hidden md:flex items-center space-x-4 lg:space-x-6 mx-6">
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
      
      <div className="hidden md:flex items-center ml-auto gap-2">
        <div className={cn(
          "flex items-center gap-2 text-xs px-3 py-1 rounded-full",
          connectionStatus === 'connected' ? "bg-green-500/10 text-green-400" : 
          connectionStatus === 'connecting' ? "bg-yellow-500/10 text-yellow-400" : 
          "bg-red-500/10 text-red-400"
        )}>
          <div className={cn(
            "w-2 h-2 rounded-full",
            connectionStatus === 'connected' ? "bg-green-400" : 
            connectionStatus === 'connecting' ? "bg-yellow-400" : 
            "bg-red-400"
          )} />
          {connectionStatus === 'connected' ? "Connected" : 
           connectionStatus === 'connecting' ? "Connecting..." : 
           "Disconnected"}
        </div>
        
        <Button variant="outline" size="sm" className="gap-1">
          <Code className="h-4 w-4 mr-1" />
          .based
        </Button>
        
        <Button size="sm" variant="default">
          <Github className="h-4 w-4 mr-2" />
          Sign In
        </Button>
      </div>
      
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden ml-auto"
        onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
      >
        <Menu className="h-5 w-5" />
      </Button>
      
      {isMobileMenuOpen && (
        <div className="absolute top-14 left-0 right-0 bg-background border-b border-border z-50 md:hidden p-4 space-y-2">
          <Button variant="ghost" size="sm" className="w-full justify-start">
            File
          </Button>
          <Button variant="ghost" size="sm" className="w-full justify-start">
            Edit
          </Button>
          <Button variant="ghost" size="sm" className="w-full justify-start">
            View
          </Button>
          <Button variant="ghost" size="sm" className="w-full justify-start">
            Help
          </Button>
          <div className="pt-2 border-t border-border">
            <Button size="sm" variant="default" className="w-full">
              <Github className="h-4 w-4 mr-2" />
              Sign In
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}