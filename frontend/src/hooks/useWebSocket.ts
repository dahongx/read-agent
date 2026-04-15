import { useEffect, useRef, useState, useCallback } from 'react'

export type WsReadyState = 'connecting' | 'open' | 'reconnecting' | 'closed'

export interface WsMessage {
  event: string
  [key: string]: unknown
}

export function useWebSocket(sessionId: string) {
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null)
  const [readyState, setReadyState] = useState<WsReadyState>('connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmounted = useRef(false)
  const wasEverOpen = useRef(false)   // only show "reconnecting" after a real connection

  const connect = useCallback(() => {
    if (unmounted.current) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => {
      if (!unmounted.current) {
        wasEverOpen.current = true
        setReadyState('open')
      }
    }

    ws.onmessage = (e) => {
      if (!unmounted.current) {
        try {
          setLastMessage(JSON.parse(e.data) as WsMessage)
        } catch {
          // ignore non-JSON
        }
      }
    }

    ws.onclose = (e) => {
      if (unmounted.current) return
      // Normal closure (e.g., navigating away) — don't retry
      if (e.wasClean && e.code === 1000) {
        setReadyState('closed')
        return
      }
      // Only show "reconnecting" if we had a real connection before
      if (wasEverOpen.current) setReadyState('reconnecting')
      retryTimer.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [sessionId])

  useEffect(() => {
    unmounted.current = false
    connect()
    return () => {
      unmounted.current = true
      if (retryTimer.current) clearTimeout(retryTimer.current)
      wsRef.current?.close(1000, 'component unmounted')
    }
  }, [connect])

  return { lastMessage, readyState }
}
