import { useEffect, useRef, useState, useCallback } from 'react'

export type WsReadyState = 'connecting' | 'open' | 'reconnecting' | 'closed'

export interface WsMessage {
  event?: string
  terminal?: boolean
  [key: string]: unknown
}

export function useWebSocket(sessionId: string) {
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null)
  const [readyState, setReadyState] = useState<WsReadyState>('connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retryCount = useRef(0)
  const unmounted = useRef(false)
  const wasEverOpen = useRef(false)
  const terminalClose = useRef(false)

  const connect = useCallback(() => {
    if (unmounted.current || terminalClose.current) return
    if (retryCount.current >= 10) {
      setReadyState('closed')
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => {
      if (!unmounted.current) {
        retryCount.current = 0
        wasEverOpen.current = true
        setReadyState('open')
      }
    }

    ws.onmessage = (e) => {
      if (unmounted.current) return
      try {
        const parsed = JSON.parse(e.data) as WsMessage
        if (parsed.terminal === true) {
          terminalClose.current = true
          setReadyState('closed')
        }
        setLastMessage(parsed)
      } catch {
        // ignore non-JSON
      }
    }

    ws.onclose = (e) => {
      if (unmounted.current || terminalClose.current) {
        setReadyState('closed')
        return
      }
      if (e.wasClean && e.code === 1000) {
        setReadyState('closed')
        return
      }
      retryCount.current += 1
      if (wasEverOpen.current) setReadyState('reconnecting')
      else setReadyState('connecting')
      retryTimer.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [sessionId])

  useEffect(() => {
    unmounted.current = false
    terminalClose.current = false
    connect()
    return () => {
      unmounted.current = true
      if (retryTimer.current) clearTimeout(retryTimer.current)
      wsRef.current?.close(1000, 'component unmounted')
    }
  }, [connect])

  return { lastMessage, readyState }
}
