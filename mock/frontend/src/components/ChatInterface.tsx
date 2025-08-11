import { useEffect, useRef, useState } from 'react'
import type { ChatMode, Session } from '../types/chat'

export default function ChatInterface() {
  const [session, setSession] = useState<Session | null>(null)
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<ChatMode>('regular')
  const [content, setContent] = useState('')
  const [connected, setConnected] = useState(false)
  const bufferRef = useRef('')

  useEffect(() => {
    // create session on mount
    const run = async () => {
      const res = await fetch('/api/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      })
      if (res.ok) setSession(await res.json())
    }
    run()
  }, [])

  const send = async () => {
    if (!session || !input.trim()) return
    setContent('')
    setConnected(true)
    const res = await fetch(`/api/chat/sessions/${session.id}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: input, mode }),
    })
    if (!res.body) {
      setConnected(false)
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    const parseSSE = (chunkText: string) => {
      bufferRef.current += chunkText
      const parts = bufferRef.current.split('\n\n')
      // Keep last incomplete part in buffer
      bufferRef.current = parts.pop() || ''
      for (const evt of parts) {
        const lines = evt.split('\n')
        const dataLines = lines.filter((l) => l.startsWith('data:'))
        for (const dl of dataLines) {
          const jsonStr = dl.replace(/^data:\s*/, '')
          try {
            const obj = JSON.parse(jsonStr)
            if (obj.type === 'token' && obj.content) {
              setContent((c) => c + obj.content)
            }
          } catch {
            // ignore non-JSON data lines
          }
        }
      }
    }
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        parseSSE(decoder.decode(value, { stream: true }))
      }
    } finally {
      setConnected(false)
    }
    setInput('')
  }

  return (
    <div className="mt-6 border rounded p-4 space-y-3">
      <div className="flex items-center gap-2">
        <select value={mode} onChange={(e) => setMode(e.target.value as ChatMode)} className="border p-1 text-sm">
          <option value="regular">Regular</option>
          <option value="deep_research">Deep Research</option>
        </select>
        <input
          className="flex-1 border p-2 rounded"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="px-3 py-2 bg-blue-600 text-white rounded" onClick={send} disabled={!session}>
          Send
        </button>
      </div>
      <div className="min-h-[80px] border rounded p-2 text-sm whitespace-pre-wrap">
        {content}
      </div>
      <div className="text-xs text-gray-500">Session: {session?.id ?? 'creating...'} · {connected ? 'streaming' : 'idle'}</div>
    </div>
  )
}


