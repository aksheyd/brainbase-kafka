'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useToast } from '@/hooks/use-toast';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

// Provides connect, sendMessage, lastMessage, and connectionStatus
export function useWebSocket() {
  const { toast } = useToast();
  const wsRef = useRef<WebSocket | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  // Establishes a new WebSocket connection (with auto-reconnect)
  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;
    setConnectionStatus('connecting');
    const ws = new WebSocket('ws://localhost:8000/ws');
    wsRef.current = ws;

    ws.onopen = () => setConnectionStatus('connected');
    ws.onclose = () => {
      setConnectionStatus('disconnected');

      toast({
        title: "Connection Lost",
        description: "Connection to server lost. Attempting to reconnect in  5 seconds...",
        variant: "destructive",
      });
      // Try to reconnect after a short delay
      reconnectTimeout.current = setTimeout(connect, 50000);
    };
    ws.onerror = () => setConnectionStatus('disconnected');
    ws.onmessage = (event) => setLastMessage(event.data);
  }, []);

  // Sends a JSON-encoded message if the socket is open
  const sendMessage = useCallback((msg: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  // Connect on mount, clean up on unmount
  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { connect, sendMessage, lastMessage, connectionStatus };
}