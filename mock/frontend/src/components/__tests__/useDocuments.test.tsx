import { describe, expect, it, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useDocuments } from '../../hooks/useDocuments'

global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  if (typeof input === 'string' && input.endsWith('/api/documents') && (!init || init.method === 'GET')) {
    return new Response(JSON.stringify({ documents: [] }), { status: 200 }) as any
  }
  if (typeof input === 'string' && input.includes('/api/documents/') && init?.method === 'DELETE') {
    return new Response('{}', { status: 200 }) as any
  }
  return new Response('{}', { status: 200 }) as any
}) as any

vi.mock('../../api/client', () => ({
  apiGet: vi.fn(async () => ({ data: { documents: [] } })),
  apiUpload: vi.fn(async () => ({ data: { documents: [], errors: [] } })),
}))

describe('useDocuments', () => {
  it('initially loads documents and supports upload/remove', async () => {
    const { result } = renderHook(() => useDocuments())
    await act(async () => {})
    expect(result.current.documents).toEqual([])
    await act(async () => {
      await result.current.upload([new File(['x'], 'x.txt', { type: 'text/plain' })])
    })
    await act(async () => {
      await result.current.remove('id')
    })
  })
})


