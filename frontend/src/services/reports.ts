import { API_BASE_URL } from './api'

export async function downloadTextReport(documentId: string, fileName: string) {
  const token = localStorage.getItem('cv_token')
  const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(documentId)}/report`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error('Could not download this report')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${fileName}-citeverify.txt`
  anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
