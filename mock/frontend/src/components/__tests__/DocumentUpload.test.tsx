import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import DocumentUpload from '../../components/DocumentUpload'

vi.mock('../../api/client', () => ({
  apiUpload: vi.fn(async () => ({ data: { documents: [], errors: [] } })),
}))

describe('DocumentUpload', () => {
  it('renders and uploads files', async () => {
    const onUploaded = vi.fn()
    render(<DocumentUpload onUploaded={onUploaded} />)
    const input = screen.getByTestId('upload-input') as HTMLInputElement
    const file = new File(['hello'], 'hello.txt', { type: 'text/plain' })
    await waitFor(() => fireEvent.change(input, { target: { files: [file] } }))
    await waitFor(() => expect(onUploaded).toHaveBeenCalled())
  })
})


