import { useEffect, useState, useRef, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws'

interface WebSocketMessage {
  type: string
  [key: string]: any
}

export function useWebSocket(onMessage?: (message: WebSocketMessage) => void) {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const reconnectAttemptsRef = useRef(0)

  const connect = useCallback(() => {
    try {
      console.log('🔌 Connecting to WebSocket:', WS_URL)
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('✅ WebSocket connected')
        setIsConnected(true)
        setConnectionError(null)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('📨 WebSocket message:', data)

          // Handle connection confirmation
          if (data.type === 'connection_confirmed' || data.type === 'pong') {
            setIsConnected(true)
            setConnectionError(null)
          }

          // Call custom message handler
          if (onMessage) {
            onMessage(data)
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        if (ws.readyState !== WebSocket.OPEN) {
          setConnectionError('Connection failed')
        }
      }

      ws.onclose = () => {
        console.log('🔴 WebSocket disconnected')
        setIsConnected(false)
        wsRef.current = null

        // Attempt to reconnect with exponential backoff
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
        console.log(`🔄 Reconnecting in ${delay}ms...`)
        
        reconnectTimeoutRef.current = window.setTimeout(() => {
          reconnectAttemptsRef.current++
          connect()
        }, delay)
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      setConnectionError('Failed to connect')
    }
  }, [onMessage])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket not connected, cannot send message')
    }
  }, [])

  return {
    isConnected,
    connectionError,
    sendMessage,
  }
}

