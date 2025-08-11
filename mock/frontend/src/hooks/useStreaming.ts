import { useEffect, useRef, useState } from 'react'
import { openSSE } from '../api/client'

export function useStreaming(path?: string) {
  const [content, setContent] = useState('')
  const [connected, setConnected] = useState(false)
  const sourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!path) return
    const es = openSSE(path, (event) => {
      // event.data may include JSON; for simplicity append raw line
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'token' && data.content) setContent((c) => c + data.content)
      } catch {
        // ignore non-JSON
      }
    })
    sourceRef.current = es
    setConnected(true)
    es.onerror = () => setConnected(false)
    return () => {
      es.close()
      setConnected(false)
    }
  }, [path])

  const reset = () => setContent('')

  return { content, connected, reset }
}


