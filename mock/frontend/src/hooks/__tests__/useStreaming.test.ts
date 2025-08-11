import { describe, expect, it, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useStreaming } from '../../hooks/useStreaming'

class FakeEventSource {
  url: string
  onmessage: ((this: EventSource, ev: MessageEvent) => any) | null = null
  onerror: ((this: EventSource, ev: Event) => any) | null = null
  constructor(url: string) {
    this.url = url
    // no-op
  }
  close() {
    // no-op
  }
}

vi.mock('../../api/client', () => ({
  openSSE: (path: string, onMessage: (event: MessageEvent) => void) => {
    const es = new FakeEventSource(path) as unknown as EventSource
    // Immediately simulate a message for testing
    setTimeout(() => {
      onMessage(new MessageEvent('message', { data: JSON.stringify({ type: 'token', content: 'Hello' }) }))
      onMessage(new MessageEvent('message', { data: JSON.stringify({ type: 'token', content: ' World' }) }))
    }, 0)
    return es
  },
}))

describe('useStreaming', () => {
  it('accumulates streamed content from SSE', async () => {
    const { result } = renderHook(() => useStreaming('/api/stream'))
    // Wait for microtasks
    await act(async () => {
      await new Promise((r) => setTimeout(r, 10))
    })
    expect(result.current.content).toBe('Hello World')
    expect(result.current.connected).toBe(true)
  })
})


