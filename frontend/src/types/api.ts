export type User = {
  id: string
  name: string
  email: string
}

export type AuthResponse = {
  token: string
  user: User
}

export type Claim = {
  id: string
  text: string
  status: string
  citations: { id?: string; label: string }[]
  evidence: string
  explanation: string
  limitations: string[]
  source: unknown
}

export type DocumentRecord = {
  id: string
  fileName: string
  uploadedAt: string
  status: string
  report: {
    summary: string
    claims: Claim[]
    citations: unknown[]
    statistics: Record<string, number | string>
  }
}

export type DashboardResponse = {
  totalDocuments: number
  totalClaims: number
  supported: number
  partiallySupported: number
  unsupported: number
  contradicted: number
  unverifiable: number
  recentDocuments: DocumentRecord[]
}
