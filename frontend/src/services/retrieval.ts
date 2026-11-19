import type { EvidencePassage } from './verification'

export type RetrievalEvidenceResponse = {
  claim_id: string
  evidence: EvidencePassage[]
  retrieval_status: 'resolved' | 'full_text_available' | 'ambiguous' | 'not_found' | 'metadata_only'
  source_limitations: string[]
}

// Member 2 integration is intentionally adapter-only until a mounted endpoint
// and response contract are confirmed. Do not present placeholder evidence as real.
export function unavailableRetrieval(): RetrievalEvidenceResponse {
  return {
    claim_id: '',
    evidence: [],
    retrieval_status: 'not_found',
    source_limitations: ['A Member 2 research-evidence endpoint is not currently connected.'],
  }
}
