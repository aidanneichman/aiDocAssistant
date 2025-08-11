export type DocumentMetadata = {
  id: string
  original_filename: string
  content_type: string
  size_bytes: number
  upload_time: string
}

export type DocumentListResponse = {
  documents: DocumentMetadata[]
}

export type UploadErrorItem = {
  filename: string
  code: string
  message: string
}

export type DocumentUploadResponse = {
  documents: DocumentMetadata[]
  errors: UploadErrorItem[]
}


