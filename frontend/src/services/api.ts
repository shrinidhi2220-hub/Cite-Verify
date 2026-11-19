export const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') || '/api'

export type ApiErrorShape = {
  error?: string
  detail?: string | { msg?: string }[]
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json().catch(() => null)
  }
  return response.text().catch(() => '')
}

export function getErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') return fallback
  const shape = payload as ApiErrorShape
  if (typeof shape.error === 'string') return shape.error
  if (typeof shape.detail === 'string') return shape.detail
  if (Array.isArray(shape.detail)) {
    const messages = shape.detail
      .map(item => item?.msg)
      .filter((item): item is string => Boolean(item))
    if (messages.length) return messages.join(', ')
  }
  return fallback
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true,
): Promise<T> {
  const token = authenticated ? localStorage.getItem('cv_token') : null
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  const payload = await readResponse(response)
  if (!response.ok) {
    throw new ApiError(getErrorMessage(payload, 'Request failed'), response.status)
  }
  return payload as T
}
