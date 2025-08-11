import { useState } from 'react'
import { apiUpload } from '../api/client'

type UploadResponse = {
  documents: Array<{ id: string; original_filename: string }>
  errors: Array<{ filename: string; code: string; message: string }>
}

export default function DocumentUpload({ onUploaded }: { onUploaded?: () => void }) {
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : []
    if (!files.length) return
    setIsUploading(true)
    setError(null)
    const res = await apiUpload<UploadResponse>('/api/documents/upload', files)
    setIsUploading(false)
    if (res.error) setError(res.error)
    onUploaded?.()
  }

  return (
    <div>
      <label className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded cursor-pointer">
        <input
          type="file"
          multiple
          className="hidden"
          onChange={handleChange}
          aria-label="Upload Documents"
          data-testid="upload-input"
        />
        Upload Documents
      </label>
      {isUploading && <p className="text-sm text-gray-600 mt-2">Uploading...</p>}
      {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
    </div>
  )
}


