import { useEffect, useState } from 'react'

const STORAGE_KEY = 'read_agent_user_id'

function readStored(): string {
  if (typeof window === 'undefined') return ''
  try {
    return window.localStorage.getItem(STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

function writeStored(value: string) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, value)
  } catch {
    // ignore
  }
}

export function getUserId(): string {
  return readStored()
}

export function setUserId(value: string) {
  writeStored(value.trim())
  // 通知所有 hook 同步
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('user-id-changed'))
  }
}

export function useUserId(): [string, (value: string) => void] {
  const [userId, setUserIdState] = useState<string>(readStored())

  useEffect(() => {
    function onChange() {
      setUserIdState(readStored())
    }
    window.addEventListener('user-id-changed', onChange)
    window.addEventListener('storage', onChange)
    return () => {
      window.removeEventListener('user-id-changed', onChange)
      window.removeEventListener('storage', onChange)
    }
  }, [])

  return [userId, (v: string) => {
    writeStored(v.trim())
    setUserIdState(v.trim())
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('user-id-changed'))
    }
  }]
}

export function withUserQuery(url: string): string {
  const uid = getUserId()
  if (!uid) return url
  const sep = url.includes('?') ? '&' : '?'
  return `${url}${sep}user_id=${encodeURIComponent(uid)}`
}
