const citationPattern = /\[([^\]]+)\]|\(([^()]*(?:doi|https?:\/\/|pp\.?|et al\.)[^()]*)\)|\b(?:[A-Z][A-Za-z'-]+(?: et al\.?| and [A-Z][A-Za-z'-]+)?),?\s+\((?:19|20)\d{2}[a-z]?\)/g;

function extractCitations(text) {
  const matches = [];
  const seen = new Set();
  for (const match of text.matchAll(citationPattern)) {
    const citation = (match[0] || '').trim();
    if (citation && !seen.has(citation)) {
      seen.add(citation);
      matches.push({ id: `cite_${matches.length + 1}`, label: citation, raw: citation });
    }
  }
  return matches;
}

function extractClaims(text, citations) {
  const lines = text
    .replace(/\r/g, '')
    .split(/\n+/)
    .map(line => line.replace(/\s+/g, ' ').trim())
    .filter(line => line.length >= 45 && line.length <= 500);

  const scientificKeywords = /\b(show|found|demonstrate|demonstrates|indicate|indicates|results|revealed|associated|significant|increases|decreases|correlat|evidence|study|research|effect|risk|conclusion)\b/i;
  const candidates = lines.filter(line => scientificKeywords.test(line)).slice(0, 12);

  return candidates.map((line, index) => {
    const associated = citations.filter(citation => line.includes(citation.label));
    return {
      id: `claim_${index + 1}`,
      text: line,
      citations: associated.length ? associated : [],
    };
  });
}

function classifyClaim(claim) {
  if (!claim.citations.length) {
    return {
      status: 'UNVERIFIABLE',
      evidence: 'No associated citation was identified.',
      explanation: 'The claim could not be evaluated because no source citation could be mapped to it.',
      limitations: ['Citation metadata was not available.', 'No scientific source was retrieved.'],
    };
  }

  return {
    status: 'UNVERIFIABLE',
    evidence: 'Citation metadata was extracted, but source text was not available.',
    explanation: 'The citation is associated with the claim, but CiteVerify has not retrieved and examined source evidence.',
    limitations: ['External scientific source retrieval is not configured.', 'No claim-support judgement can be made without source content.'],
  };
}

function buildReport(fileName, text) {
  const citations = extractCitations(text);
  const claims = extractClaims(text, citations).map(claim => {
    const result = classifyClaim(claim);
    return {
      ...claim,
      ...result,
      source: claim.citations.length
        ? { title: claim.citations[0].label, retrieved: false, url: null }
        : null,
    };
  });

  const counts = claims.reduce((totals, claim) => {
    totals[claim.status] = (totals[claim.status] || 0) + 1;
    return totals;
  }, {});

  return {
    fileName,
    summary: text
      ? text.replace(/\s+/g, ' ').trim().slice(0, 900)
      : 'No extractable text was found in the document.',
    extractedTextLength: text.length,
    citations,
    claims,
    statistics: {
      totalClaims: claims.length,
      supported: counts.SUPPORTED || 0,
      partiallySupported: counts['PARTIALLY SUPPORTED'] || 0,
      unsupported: counts.UNSUPPORTED || 0,
      contradicted: counts.CONTRADICTED || 0,
      unverifiable: counts.UNVERIFIABLE || 0,
      mode: 'Rule-based extraction only; no source verification',
    },
  };
}

module.exports = { extractCitations, extractClaims, buildReport };
