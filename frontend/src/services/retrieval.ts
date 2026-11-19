import { getErrorMessage, ApiError } from './api'
import type { VerificationJobAccepted } from './verification'

export type ResearchEvidenceRequest = {
  claim_id: string
  claim_text: string
  search_query?: string
  citation_title?: string
  citation_doi?: string
  citation_authors?: string[]
  publication_year?: number
  citation_ids?: string[]
  claim_type?: string
  per_page?: number
  top_k?: number
  max_papers?: number
}

export async function runResearchVerification(
  request: ResearchEvidenceRequest,
): Promise<VerificationJobAccepted> {
  const apiBase =
    (import.meta.env.VITE_VERIFICATION_API_URL as string | undefined)?.replace(/\/$/, '')
    || 'http://localhost:8000/api'

  const response = await fetch(`${apiBase}/v1/verification/run-from-research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(getErrorMessage(payload, 'Unable to start research verification'), response.status)
  }
  return payload as VerificationJobAccepted
}