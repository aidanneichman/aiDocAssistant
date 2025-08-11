import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ChatInterface from '../../components/ChatInterface'

vi.mock('../../hooks/useStreaming', () => ({
  useStreaming: () => ({ content: 'Hello stream', connected: true, reset: vi.fn() }),
}))

describe('ChatInterface', () => {
  it('creates a session on mount and sends a message', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/chat/sessions') && (!init || init.method === 'POST')) {
        return new Response(JSON.stringify({ id: 'session-1', mode: 'regular', document_ids: [] }), { status: 200 }) as any
      }
      if (url.includes('/api/chat/sessions/') && init?.method === 'POST') {
        return new Response('event: token\n' + 'data: {"type":"token","content":"Hi"}\n\n', {
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
        }) as any
      }
      return new Response('{}', { status: 200 }) as any
    }) as any
    // @ts-ignore
    global.fetch = fetchMock

    render(<ChatInterface />)

    // Wait for session to be created
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())

    const input = screen.getByPlaceholderText(/type your message/i) as HTMLInputElement
    fireEvent.change(input, { target: { value: 'Hello' } })
    const sendBtn = screen.getByText(/send/i)
    fireEvent.click(sendBtn)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))

    // Streaming content shown from mocked SSE body
    expect(screen.getByText(/Hi/)).toBeInTheDocument()
  })
})


