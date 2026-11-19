import { apiRequest } from './api'
import type { AuthResponse, User } from '../types/api'

export async function register(name: string, email: string, password: string) {
  return apiRequest<AuthResponse>(
    '/auth/register',
    { method: 'POST', body: JSON.stringify({ name, email, password }) },
    false,
  )
}

export async function login(email: string, password: string) {
  return apiRequest<AuthResponse>(
    '/auth/login',
    { method: 'POST', body: JSON.stringify({ email, password }) },
    false,
  )
}

export async function getCurrentUser() {
  return apiRequest<{ user: User }>('/auth/me')
}

export function saveSession(data: AuthResponse) {
  localStorage.setItem('cv_token', data.token)
  localStorage.setItem('cv_user', JSON.stringify(data.user))
}

export function clearSession() {
  localStorage.removeItem('cv_token')
  localStorage.removeItem('cv_user')
}
