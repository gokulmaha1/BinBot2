"use client";

import { useEffect, useState, useRef } from "react";

interface WebSocketHook {
  isConnected: boolean;
  lastMessage: any;
  send: (data: any) => void;
}

export function useWebSocket(userId: string | null, baseUrl?: string): WebSocketHook {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!userId) return;

    const url = baseUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const wsUrl = url.replace("http", "ws").replace("https", "wss");
    const ws = new WebSocket(`${wsUrl}/api/ws/${userId}`);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLastMessage(data);
    };

    return () => {
      ws.close();
    };
  }, [userId, baseUrl]);

  const send = (data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  };

  return { isConnected, lastMessage, send };
}
