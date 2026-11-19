import { API_BASE_URL, getErrorMessage, ApiError } from './api'

export type VerificationVerdict =
  | 'SUPPORTED'
  | 'PARTIALLY_SUPPORTED'
  | 'UNSUPPORTED'
  | 'CONTRADICTED'
  | 'INSUFFICIENT_EVIDENCE'
  | 'POSSIBLY_OUTDATED'

export type EvidenceStrength = 'LOW' | 'MEDIUM' | 'HIGH'
export type VerificationMethod = 'rule_based' | 'llm_assisted' | 'human_review'

export type EvidencePassage = {
  evidence_id: string
  source_id: string
  source_title?: string | null
  text: string
  page_number?: number | null
  section_name?: string | null
  source_type?: 'full_text' | 'abstract' | 'metadata_only' | 'unknown'
  retrieval_score?: number | null
}

export type VerificationRequest = {
  claim_id: string
  claim_text: string
  citation_ids?: string[]
  claim_type?: string | null
  evidence?: EvidencePassage[]
  retrieval_status?: 'resolved' | 'full_text_available' | 'ambiguous' | 'not_found' | 'metadata_only'
  source_limitations?: string[]
}

export type NumericalDiscrepancy = {
  claim_value: string
  evidence_value: string
  unit?: string | null
  description: string
}

export type VerdictDecision = {
  claim_id: string
  verdict: VerificationVerdict
  explanation: string
  supporting_evidence_ids: string[]
  contradicting_evidence_ids: string[]
  neutral_evidence_ids: string[]
  numerical_discrepancies: NumericalDiscrepancy[]
  evidence_strength: EvidenceStrength
  limitations: string[]
  human_review_required: boolean
  method: VerificationMethod
}

export type VerificationJobAccepted = {
  job_id: string
  status: 'queued'
  status_url: string
  message: string
}

export type VerificationJobStatus = {
  job_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  result: VerdictDecision | null
  error: string | null
}

export async function runVerification(request: VerificationRequest): Promise<VerificationJobAccepted> {
  const verificationApiBase =
    (import.meta.env.VITE_VERIFICATION_API_URL as string | undefined)?.replace(/\/$/, '') || API_BASE_URL
  const response = await fetch(`${verificationApiBase}/v1/verification/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(getErrorMessage(payload, 'Unable to start verification'), response.status)
  }
  return payload as VerificationJobAccepted
}

export async function getVerificationStatus(jobId: string): Promise<VerificationJobStatus> {
  const verificationApiBase =
    (import.meta.env.VITE_VERIFICATION_API_URL as string | undefined)?.replace(/\/$/, '') || API_BASE_URL
  const response = await fetch(`${verificationApiBase}/v1/verification/status/${encodeURIComponent(jobId)}`)
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(getErrorMessage(payload, 'Unable to retrieve verification status'), response.status)
  }
  return payload as VerificationJobStatus
}
