export type User = {
  id: string
  name: string
  email: string
}

export type AuthResponse = {
  token: string
  user: User
}

export type BibliographyReference = {
  id: string
  number: number | null
  label: string
  raw: string
  title: string
  authors: string[]
  publicationYear: number | null
  doi: string | null
  doiStatus: string
  doiSource?: string | null
  doiConfidence?: number | null
}

export type Claim = {
  id: string
  text: string
  status: string
  citations: { id?: string; label: string; referenceIds?: string[] }[]
  referenceIds?: string[]
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
    citations: { id?: string; label: string; referenceIds?: string[] }[]
    references?: BibliographyReference[]
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
