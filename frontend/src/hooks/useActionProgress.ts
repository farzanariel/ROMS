import { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';

export interface ProgressUpdate {
  type: string;
  current: number;
  total: number;
  message: string;
  order?: {
    id: number;
    product: string;
    price: string;
    orderNumber: string;
    email: string;
    quantity: string;
    status: string;
  };
}

export const useActionProgress = () => {
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [clientId] = useState(uuidv4());
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    // Don't create multiple connections
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/ws/actions/${clientId}`;
    
    console.log('🔌 Connecting to WebSocket:', wsUrl);
    console.log('🆔 Client ID:', clientId);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

        ws.onopen = () => {
          console.log('✅ WebSocket connected successfully');
          setIsConnected(true);
          setConnectionError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('📨 Received:', data);
            
            if (data.type === 'progress') {
              console.log('📊 Setting progress:', data);
              setProgress(data);
            } else if (data.type === 'order_parsed') {
              console.log('📦 New order parsed:', data.order);
              // Store order data in progress for the Actions component to pick up
              setProgress(prev => ({
                ...prev,
                type: 'order_parsed',
                order: data.order,
                current: prev?.current || 0,
                total: prev?.total || 1,
                message: prev?.message || 'Processing...'
              }));
            } else if (data.type === 'connection_confirmed') {
              console.log('✅ Connection confirmed for client:', data.client_id);
              // Clear any connection errors when we get confirmation
              setConnectionError(null);
              setIsConnected(true);
            } else if (data.type === 'pong') {
              // Connection is alive - clear any errors
              setConnectionError(null);
              if (!isConnected) {
                setIsConnected(true);
              }
            }
          } catch (error) {
            console.error('❌ Failed to parse message:', error);
          }
        };

    ws.onclose = (event) => {
      console.log('🔌 WebSocket closed:', event.code, event.reason);
      setIsConnected(false);
      wsRef.current = null;
      
      // Only reconnect if it wasn't closed intentionally
      if (event.code !== 1000 && event.code !== 1001) {
        console.log('🔄 Reconnecting in 2 seconds...');
        reconnectTimeoutRef.current = setTimeout(() => {
          // Recursive call to the effect by updating state won't work
          // Just try to connect again directly
          const retryWs = new WebSocket(wsUrl);
          wsRef.current = retryWs;
          
          retryWs.onopen = ws.onopen;
          retryWs.onmessage = ws.onmessage;
          retryWs.onclose = ws.onclose;
          retryWs.onerror = ws.onerror;
        }, 2000);
      }
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      // Only set error if we're not already connected
      // (minor errors can happen even when connection is working)
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        setConnectionError('Connection failed');
        setIsConnected(false);
      }
    };

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000); // Normal closure
      }
    };
  }, [clientId]);

  return { progress, clientId, isConnected, connectionError };
};