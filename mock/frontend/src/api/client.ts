export type ApiResult<T> = { data?: T; error?: string }

const BASE_URL = '' // proxied by Vite dev server

export async function apiGet<T>(path: string): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${BASE_URL}${path}`)
    if (!res.ok) throw new Error(await res.text())
    return { data: (await res.json()) as T }
  } catch (e: any) {
    return { error: e?.message ?? 'Request failed' }
  }
}

export async function apiUpload<T>(path: string, files: File[]): Promise<ApiResult<T>> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f, f.name))
  try {
    const res = await fetch(`${BASE_URL}${path}`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(await res.text())
    return { data: (await res.json()) as T }
  } catch (e: any) {
    return { error: e?.message ?? 'Upload failed' }
  }
}

export function openSSE(path: string, onMessage: (event: MessageEvent) => void): EventSource {
  const es = new EventSource(`${BASE_URL}${path}`)
  es.onmessage = onMessage
  return es
}


