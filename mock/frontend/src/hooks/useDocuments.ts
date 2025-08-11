import { useCallback, useEffect, useState } from 'react'
import { apiGet, apiUpload } from '../api/client'
import type { DocumentListResponse, DocumentMetadata, DocumentUploadResponse } from '../types/document'

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentMetadata[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    const res = await apiGet<DocumentListResponse>('/api/documents')
    setLoading(false)
    if (res.error) setError(res.error)
    if (res.data) setDocuments(res.data.documents)
  }, [])

  const upload = useCallback(async (files: File[]) => {
    setLoading(true)
    const res = await apiUpload<DocumentUploadResponse>('/api/documents/upload', files)
    setLoading(false)
    if (res.error) setError(res.error)
    await refresh()
    return res
  }, [refresh])

  const remove = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    const res = await fetch(`/api/documents/${id}`, { method: 'DELETE' })
    setLoading(false)
    if (!res.ok) setError(await res.text())
    await refresh()
  }, [refresh])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { documents, loading, error, refresh, upload, remove }
}


