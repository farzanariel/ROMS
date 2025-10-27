import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface WebSocketMessage {
  type: 'data_update' | 'cell_edit' | 'connection_status'
  update_type?: string
  data?: any
  row_id?: string
  column?: string
  old_value?: string
  new_value?: string
  user_id?: string
  timestamp?: number
}

export const useWebSocket = (sheetUrl: string) => {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const queryClient = useQueryClient()
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10 // Increased for mobile
  const heartbeatIntervalRef = useRef<NodeJS.Timeout>()
  const isPageVisible = useRef(true)

  const connect = () => {
    if (!sheetUrl || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }

    try {
      // Encode the sheet URL for the WebSocket path
      const encodedSheetUrl = encodeURIComponent(sheetUrl)
      
      // Use the same host as the current page for WebSocket connection
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.hostname === 'localhost' ? 'localhost' : window.location.hostname
      const wsUrl = `${protocol}//${host}:8000/ws/${encodedSheetUrl}`
      
      console.log('Connecting to WebSocket:', wsUrl)
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('✅ WebSocket connected')
        setIsConnected(true)
        reconnectAttempts.current = 0
        
        // Send initial ping to confirm connection
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'ping' }))
        }
        
        // Start heartbeat to keep connection alive
        startHeartbeat()
        
        // Only show notification on first connect or reconnect after failure
        if (reconnectAttempts.current > 0) {
          toast.success('Reconnected to live updates', { duration: 2000 })
        }
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      wsRef.current.onclose = () => {
        console.log('🔌 WebSocket disconnected')
        setIsConnected(false)
        attemptReconnect()
      }

      wsRef.current.onerror = (error) => {
        console.error('❌ WebSocket error:', error)
        setIsConnected(false)
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      attemptReconnect()
    }
  }

  const startHeartbeat = () => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
    }
    
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 15000) // Send ping every 15 seconds
  }

  const stopHeartbeat = () => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = null
    }
  }

  const attemptReconnect = () => {
    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.log('Max reconnection attempts reached')
      toast.error('Live updates disconnected. Please refresh the page.')
      return
    }

    // More aggressive reconnection for mobile
    const delay = Math.min(1000 * Math.pow(1.5, reconnectAttempts.current), 15000) // Faster backoff
    reconnectAttempts.current++

    console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current})`)
    
    reconnectTimeoutRef.current = setTimeout(() => {
      connect()
    }, delay)
  }

  const lastNotificationTime = useRef<number>(0)
  const notificationCooldown = 30000 // 30 seconds between notifications

  const handleMessage = (message: WebSocketMessage) => {
    const now = Date.now()
    const shouldShowNotification = now - lastNotificationTime.current > notificationCooldown

    console.log('🔄 WebSocket message received:', message.type, message.update_type)

    switch (message.type) {
      case 'connection_status':
        // Handle connection status messages from server
        console.log('📡 Connection status:', message)
        break

      case 'pong':
        // Heartbeat response - connection is alive
        // No action needed, just acknowledge
        break

      case 'data_update':
        // Invalidate relevant queries to trigger refetch
        if (message.update_type === 'overview') {
          // Invalidate all orders-overview queries (with and without sheetUrl)
          queryClient.invalidateQueries({ queryKey: ['orders-overview'] })
          
          // Only show notification for significant changes and respect cooldown
          if (shouldShowNotification && message.data?.pending_orders > 0) {
            toast('📊 Data refreshed', { duration: 2000 })
            lastNotificationTime.current = now
          }
        } else if (message.update_type === 'new_order') {
          // Invalidate all related queries
          queryClient.invalidateQueries({ queryKey: ['orders-overview'] })
          queryClient.invalidateQueries({ queryKey: ['pending-orders'] })
          queryClient.invalidateQueries({ queryKey: ['all-orders'] })
          
          if (shouldShowNotification) {
            toast.success('📝 New order added!')
            lastNotificationTime.current = now
          }
        } else if (message.update_type === 'row_update') {
          // Invalidate all related queries
          queryClient.invalidateQueries({ queryKey: ['orders-overview'] })
          queryClient.invalidateQueries({ queryKey: ['pending-orders'] })
          queryClient.invalidateQueries({ queryKey: ['all-orders'] })
          
          // Don't show notification for row updates since user initiated them
        }
        break

      case 'cell_edit':
        // Only show for external edits and respect cooldown
        if (message.user_id !== 'current_user' && shouldShowNotification) {
          toast(`📝 ${message.column} updated externally`, {
            duration: 3000,
            icon: '⚡',
          })
          lastNotificationTime.current = now
        }
        
        // Always invalidate queries to show updated data
        // Invalidate all variations of the queries to ensure dashboard updates
        queryClient.invalidateQueries({ queryKey: ['orders-overview'] })
        queryClient.invalidateQueries({ queryKey: ['pending-orders'] })
        queryClient.invalidateQueries({ queryKey: ['all-orders'] })
        
        // Force refetch of all data to ensure dashboard updates
        queryClient.refetchQueries({ queryKey: ['orders-overview'] })
        break

      default:
        console.log('Unknown message type:', message.type)
    }
  }

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    
    stopHeartbeat()
    
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    
    setIsConnected(false)
  }

  useEffect(() => {
    if (sheetUrl) {
      connect()
    }

    // Handle page visibility changes (mobile app switching, etc.)
    const handleVisibilityChange = () => {
      isPageVisible.current = !document.hidden
      
      if (isPageVisible.current && wsRef.current?.readyState !== WebSocket.OPEN) {
        // Page became visible and WebSocket is not open, try to reconnect
        console.log('Page became visible, attempting to reconnect...')
        setTimeout(() => connect(), 1000)
      }
    }

    // Handle online/offline events
    const handleOnline = () => {
      console.log('Network came back online, attempting to reconnect...')
      setTimeout(() => connect(), 1000)
    }

    const handleOffline = () => {
      console.log('Network went offline')
      setIsConnected(false)
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      disconnect()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [sheetUrl])

  return {
    isConnected,
    connect,
    disconnect
  }
}
