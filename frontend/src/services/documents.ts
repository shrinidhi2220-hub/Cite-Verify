import { API_BASE_URL, apiRequest } from './api'
import type { DashboardResponse, DocumentRecord } from '../types/api'

export async function getDashboard() {
  return apiRequest<DashboardResponse>('/dashboard')
}

export async function getDocuments() {
  return apiRequest<{ documents: DocumentRecord[] }>('/documents')
}

export async function getDocument(documentId: string) {
  return apiRequest<DocumentRecord>(`/documents/${encodeURIComponent(documentId)}`)
}

export async function uploadDocument(
  file: File,
  onProgress: (percent: number) => void,
) {
  return new Promise<DocumentRecord>((resolve, reject) => {
    const token = localStorage.getItem('cv_token')
    const form = new FormData()
    form.append('file', file)
    const request = new XMLHttpRequest()
    request.open('POST', `${API_BASE_URL}/documents`)
    if (token) request.setRequestHeader('Authorization', `Bearer ${token}`)

    request.upload.addEventListener('progress', event => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    })

    request.addEventListener('load', () => {
      let payload: { error?: string }
      try {
        payload = JSON.parse(request.responseText) as { error?: string }
      } catch {
        reject(new Error('Unexpected server response'))
        return
      }
      if (request.status >= 200 && request.status < 300) {
        resolve(payload as DocumentRecord)
      } else {
        reject(new Error(payload.error || 'Upload failed'))
      }
    })
    request.addEventListener('error', () => reject(new Error('Upload connection failed')))
    request.addEventListener('abort', () => reject(new Error('Upload was cancelled')))
    request.send(form)
  })
}
