const NUMERIC_CITATION_PATTERN = /\[\s*\d+(?:\s*[-–,;]\s*\d+)*\s*\]/g;
const AUTHOR_YEAR_CITATION_PATTERN = /\b[A-Z][A-Za-z'-]+(?:\s+et\s+al\.?|\s+and\s+[A-Z][A-Za-z'-]+)?,?\s+\((?:19|20)\d{2}[a-z]?\)/g;
const PARENTHETICAL_CITATION_PATTERN = /\((?=[^()]{0,120}(?:\bet\s+al\.?\b|\b(?:19|20)\d{2}\b))[^()]{3,120}\)/g;
const DOI_PATTERN = /\b10\.\d{4,9}\/[0-9A-Z._;()/:+-]+/i;

const FACTUAL_PREDICATE_PATTERN = /\b(?:is|are|was|were|has|have|had|uses?|used|using|relies|rely|relied|contains?|contained|includes?|included|consists?|comprises?|demonstrates?|demonstrated|shows?|showed|finds?|found|reports?|reported|indicates?|indicated|suggests?|suggested|increases?|increased|decreases?|decreased|reduces?|reduced|improves?|improved|affects?|affected|causes?|caused|results?|resulted|correlates?|correlated|associates?|associated|leads?|led|produces?|produced|requires?|required|supports?|supported|outperforms?|achieves?|achieved|measures?|measured|observes?|observed|dispenses?|dispensed|provides?|provided|prevents?|prevented|predicts?|predicted|estimates?|estimated|compares?|compared|identifies?|identified|reveals?|revealed|explains?|explained|depends|depend|depends\s+on)\b/i;

const NON_CLAIM_PATTERN = [
  /^(?:please\s+)?(?:set|keep|take|use|avoid|ensure|make|click|open|show|select|choose|upload|download|try|go|visit|save|report|turn|switch|enable|disable|write|read|submit|complete|create|install|run|start|stop|check|remember|consider)\b/i,
  /^(?:if\s+you|when\s+you|whenever\s+you|during\b|before\s+you|after\s+you)\b/i,
  /\b(?:you\s+should|you\s+must|you\s+need\s+to|we\s+recommend|it\s+is\s+recommended|should\s+be\s+done)\b/i,
  /\b(?:we|i)\s+(?:hereby\s+)?(?:affirm|declare|certify|confirm)\b/i,
  /\b(?:own\s+effort|not\s+been\s+copied|not\s+copied|not\s+plagiarized|not\s+reproduced|original\s+work)\b/i,
  /\b(?:submitted\s+by|submitted\s+to|partial\s+fulfillment|department\s+of|college\s+name|university\s+name|team\s+id|srn\b|student\s+name)\b/i,
  /^(?:references|bibliography|works\s+cited|contents|acknowledg(?:e)?ments|abstract|introduction|conclusion|page\s+\d+)\b/i,
  /^(?:\d+\s*(?:of|\/)\s*\d+|[-–—•*]+)$/i,
];

function uniquePush(matches, seen, label) {
  const citation = String(label || '').trim();
  const key = citation.toLowerCase().replace(/\s+/g, ' ');
  if (!citation || seen.has(key)) return;
  seen.add(key);
  matches.push({ id: `cite_${matches.length + 1}`, label: citation, raw: citation, referenceIds: [] });
}

function extractCitations(text) {
  const source = String(text || '').normalize('NFKC');
  const matches = [];
  const seen = new Set();

  // Numeric citations may contain ranges or multiple reference numbers.
  for (const match of source.matchAll(NUMERIC_CITATION_PATTERN)) {
    uniquePush(matches, seen, match[0]);
  }

  // Narrative author-year forms such as "Peters et al. (2018a)".
  for (const match of source.matchAll(AUTHOR_YEAR_CITATION_PATTERN)) {
    uniquePush(matches, seen, match[0]);
  }

  // Parenthetical styles often group multiple references in one set of
  // parentheses: "(Peters et al., 2018a; Radford et al., 2018)".
  // Split those into independently mappable author/year citations.
  for (const match of source.matchAll(PARENTHETICAL_CITATION_PATTERN)) {
    const value = match[0];
    const inner = value.slice(1, -1);
    const segments = inner.split(/\s*;\s*/).map(part => part.trim()).filter(Boolean);
    if (segments.length === 1) {
      if (/(?:^|\s)(?:19|20)\d{2}[a-z]?\b/i.test(segments[0])) {
        uniquePush(matches, seen, value);
      }
      continue;
    }
    for (const segment of segments) {
      if (/(?:^|\s)(?:19|20)\d{2}[a-z]?\b/i.test(segment)) {
        uniquePush(matches, seen, segment);
      }
    }
  }
  return matches;
}

function normalizeInlineCitationText(value) {
  return String(value || '')
    .normalize('NFKC')
    .replace(/[\u2010-\u2015]/g, '-')
    .replace(/[\s\u00a0]+/g, ' ')
    .trim()
    .toLocaleLowerCase();
}

function parseAuthorYearCitation(label) {
  const source = String(label || '').replace(/[()]/g, ' ');
  const keys = [];
  const pattern = /\b([A-Z][A-Za-z'’-]+)(?:\s+et\s+al\.?)?\s*,?\s*\(?\s*((?:19|20)\d{2})([a-z])?\s*\)?/gi;
  for (const match of source.matchAll(pattern)) {
    keys.push({ surname: match[1].toLowerCase(), year: Number(match[2]), suffix: (match[3] || '').toLowerCase() });
  }
  return keys;
}

function getReferenceYearKey(reference) {
  const match = String(reference.raw || '').match(/\b((?:19|20)\d{2})([a-z])?\b/i);
  return match ? { year: Number(match[1]), suffix: (match[2] || '').toLowerCase() } : null;
}

function findReferenceSection(text) {
  const source = String(text || '').replace(/\r/g, '');
  const lines = source.split('\n');
  const headingIndex = lines.findIndex(line =>
    /^\s*(?:references|bibliography|works\s+cited|literature\s+cited|reference\s+list)\s*:?(?:\s*)$/i.test(line),
  );
  if (headingIndex >= 0) return lines.slice(headingIndex + 1).join('\n');

  // PDF text extraction sometimes flattens the heading into the preceding paragraph.
  const flattenedHeading = /\b(?:references|bibliography|works\s+cited|literature\s+cited|reference\s+list)\s*:?(?=\s*(?:\[\s*\d+\s*\]|\d{1,3}[.)]\s+[A-Z]|[A-Z][A-Za-z'-]+,?\s+.{0,100}\((?:19|20)\d{2}\)))/i;
  const match = flattenedHeading.exec(source);
  return match ? source.slice(match.index + match[0].length) : '';
}

function normalizeDoi(value) {
  return String(value || '')
    .trim()
    .replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '')
    .replace(/^doi\s*:\s*/i, '')
    .replace(/[\s.,;:]+$/g, '')
    .replace(/[)\]}]+$/g, '')
    .trim();
}

function extractReferenceTitle(raw) {
  const source = String(raw || '').replace(/^\s*(?:\[\s*\d+\s*\]|\d{1,3}[.)])\s*/, '').trim();
  const quoted = source.match(/[“"]([^”"]{12,240})[”"]/);
  if (quoted) return quoted[1].trim().replace(/[.]$/, '');

  // APA-like: Author (2021). Paper title. Journal / proceedings...
  let match = source.match(/\((?:19|20)\d{2}[a-z]?\)\.?\s+(.{12,260}?)(?=\.\s+(?:In\b|Proceedings\b|Journal\b|Advances\b|arXiv\b|IEEE\b|ACM\b|NeurIPS\b|ICML\b|Nature\b|Science\b|Transactions\b)|$)/i);
  if (match) return match[1].trim().replace(/[.]$/, '');

  // Numbered proceedings references often place the title after the author list.
  match = source.match(/\.\s+([A-Z][^.!?]{12,220}?)\.\s+(?=(?:In\b|Proceedings\b|Advances\b|Journal\b|arXiv\b|IEEE\b|ACM\b|NeurIPS\b|ICML\b|Nature\b|Science\b|Transactions\b))/i);
  if (match) return match[1].trim();

  // Some entries omit parentheses around the year.
  match = source.match(/\b(?:19|20)\d{2}[a-z]?\.?\s+(.{12,220}?)(?=\.\s+(?:In\b|Proceedings\b|Advances\b|Journal\b|arXiv\b|IEEE\b|ACM\b|NeurIPS\b|ICML\b)|$)/i);
  if (match) return match[1].trim().replace(/[.]$/, '');

  return '';
}

function parseReferenceEntry(rawEntry, index) {
  const raw = String(rawEntry || '').replace(/\s+/g, ' ').trim();
  if (!raw || raw.length < 12) return null;

  const numberMatch = raw.match(/^\s*(?:\[\s*(\d+)\s*\]|(\d{1,3})[.)])\s*/);
  const number = numberMatch ? Number(numberMatch[1] || numberMatch[2]) : null;
  const doiMatch = raw.match(DOI_PATTERN);
  const doi = doiMatch ? normalizeDoi(doiMatch[0]) : null;
  const yearMatch = raw.match(/\b((?:19|20)\d{2})[a-z]?\b/);
  const publicationYear = yearMatch ? Number(yearMatch[1]) : null;
  const title = extractReferenceTitle(raw);
  const withoutLabel = raw.replace(/^\s*(?:\[\s*\d+\s*\]|\d{1,3}[.)])\s*/, '');
  const authorRegion = yearMatch ? withoutLabel.slice(0, yearMatch.index) : withoutLabel.slice(0, 100);
  const firstAuthor = authorRegion.split(/,|\band\b/i).map(part => part.trim()).find(Boolean) || '';

  return {
    id: `ref_${number || index + 1}`,
    number,
    label: number ? `[${number}]` : `Reference ${index + 1}`,
    raw,
    title: title || '',
    authors: firstAuthor ? [firstAuthor] : [],
    publicationYear,
    doi,
    doiStatus: doi ? 'FOUND_IN_BIBLIOGRAPHY' : (title ? 'TITLE_LOOKUP_REQUIRED' : 'MANUAL_REVIEW_REQUIRED'),
    doiSource: doi ? 'document_reference' : null,
    doiConfidence: doi ? 1 : null,
  };
}

function extractBibliographyReferences(text) {
  const section = findReferenceSection(text);
  if (!section.trim()) return [];

  const numberedMarkers = [...section.matchAll(/(?:^|\s)\[\s*(\d{1,3})\s*\]\s*/g)];
  let rawEntries = [];

  if (numberedMarkers.length) {
    rawEntries = numberedMarkers.map((marker, index) => {
      const start = marker.index + (marker[0].startsWith(' ') ? 1 : 0);
      const end = index + 1 < numberedMarkers.length ? numberedMarkers[index + 1].index : section.length;
      return section.slice(start, end).trim();
    });
  } else {
    const lines = section.split(/\n+/).map(line => line.trim()).filter(Boolean);
    let current = '';
    for (const line of lines) {
      // A new bibliography entry commonly begins with a surname and includes a year.
      const looksLikeEntry = /^(?:[A-Z][A-Za-z'’-]+,|[A-Z][A-Za-z'’-]+\s+[A-Z].{0,80}\((?:19|20)\d{2}\))/i.test(line);
      if (looksLikeEntry && current) {
        rawEntries.push(current);
        current = line;
      } else {
        current = current ? `${current} ${line}` : line;
      }
    }
    if (current) rawEntries.push(current);
  }

  const seen = new Set();
  return rawEntries
    .map((entry, index) => parseReferenceEntry(entry, index))
    .filter(reference => {
      if (!reference) return false;
      const key = `${reference.number || ''}:${reference.raw.toLowerCase()}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 200);
}

function mapCitationsToReferences(citations, references) {
  const byNumber = new Map(references.filter(ref => ref.number).map(ref => [ref.number, ref]));
  for (const citation of citations) {
    let matched = [];
    if (/^\s*\[/.test(citation.label)) {
      const values = citation.label.match(/\d+/g) || [];
      matched = values.map(value => byNumber.get(Number(value))).filter(Boolean);
    } else {
      const authorYearKeys = parseAuthorYearCitation(citation.label);
      for (const key of authorYearKeys) {
        const candidates = references.filter(reference => {
          const yearKey = getReferenceYearKey(reference);
          if (!yearKey || yearKey.year !== key.year) return false;
          if (key.suffix && yearKey.suffix !== key.suffix) return false;
          if (!key.suffix && yearKey.suffix) {
            // A citation without a suffix may still map to an unsuffixed entry;
            // do not arbitrarily select 2018a/2018b when both exist.
            const sameAuthorYear = references.filter(candidate => {
              const candidateYear = getReferenceYearKey(candidate);
              return candidateYear?.year === key.year
                && `${candidate.raw} ${candidate.authors.join(' ')}`.toLowerCase().includes(key.surname);
            });
            if (sameAuthorYear.length > 1) return false;
          }
          const authorText = `${reference.raw} ${reference.authors.join(' ')}`.toLowerCase();
          return new RegExp(`^\\s*${key.surname.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i').test(reference.raw)
            || authorText.includes(key.surname);
        });
        matched.push(...candidates);
      }
    }
    citation.referenceIds = [...new Set(matched.map(ref => ref.id))];
  }
  return citations;
}

function removeReferenceSection(text) {
  const source = String(text || '').replace(/\r/g, '');
  const lines = source.split('\n');
  const headingIndex = lines.findIndex(line =>
    /^\s*(?:references|bibliography|works\s+cited|literature\s+cited|reference\s+list)\s*:?(?:\s*)$/i.test(line),
  );
  if (headingIndex >= 0) return lines.slice(0, headingIndex).join('\n');

  const flattenedHeading = /\b(?:references|bibliography|works\s+cited|literature\s+cited|reference\s+list)\s*:?(?=\s*(?:\[\s*\d+\s*\]|\d{1,3}[.)]\s+[A-Z]|[A-Z][A-Za-z'-]+,?\s+.{0,100}\((?:19|20)\d{2}\)))/i;
  const match = flattenedHeading.exec(source);
  return match ? source.slice(0, match.index) : source;
}

function normalizeForExtraction(text) {
  return removeReferenceSection(text)
    .replace(/([A-Za-z])[-\u00ad]\s*\n\s*([a-z])/g, '$1$2')
    .replace(/[\r\n]+/g, ' ')
    .replace(/[\t ]+/g, ' ')
    .replace(/\s+([,.;!?])/g, '$1')
    .trim();
}

function splitSentences(text) {
  if (!text) return [];
  // "et al." is an author abbreviation, not a sentence boundary.
  const protectedText = String(text).replace(/\bet\s+al\.\s+/gi, 'et al<ETAL_DOT> ');
  return protectedText
    .split(/(?<=[.!?])\s+(?=(?:[A-Z0-9“"'(\[]))/)
    .map(sentence => sentence.replace(/et al<ETAL_DOT>/gi, 'et al.').trim())
    .filter(Boolean);
}

function cleanSentence(sentence) {
  let cleaned = String(sentence || '').trim();
  cleaned = cleaned.replace(/^.*?\bclaim\s+to\s+verify\s*:?\s*/i, '');
  cleaned = cleaned.replace(/^.*?\b(?:claim|statement)\s*:\s*/i, '');
  cleaned = cleaned.replace(/\s*(?:--|—|–)\s*(?:page\s*)?\d+\s+of\s+\d+\s*$/i, '');
  cleaned = cleaned.replace(/\s+\(?page\s+\d+(?:\s+of\s+\d+)?\)?\s*$/i, '');
  cleaned = cleaned.replace(/^[\s:|–—-]+/, '').replace(/[\s|–—-]+$/, '').trim();
  return cleaned;
}

function normalizeForDeduplication(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/\[[^\]]+\]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function isPossibleFactualClaim(sentence) {
  if (!sentence || sentence.length < 45 || sentence.length > 500) return false;
  if (NON_CLAIM_PATTERN.some(pattern => pattern.test(sentence))) return false;
  if (!/[a-z]{3}/i.test(sentence)) return false;
  if (!FACTUAL_PREDICATE_PATTERN.test(sentence)) return false;
  const words = sentence.split(/\s+/).length;
  if (words < 8) return false;
  if (/^(?:sapthagiri|university|department|section|team\s+name|srn|title)\b/i.test(sentence)) return false;
  return true;
}

function extractClaims(text, citations = []) {
  const normalizedText = normalizeForExtraction(text);
  const sentences = splitSentences(normalizedText);
  const claims = [];
  const seen = new Set();

  for (const rawSentence of sentences) {
    const sentence = cleanSentence(rawSentence);
    if (!isPossibleFactualClaim(sentence)) continue;
    const dedupeKey = normalizeForDeduplication(sentence);
    if (!dedupeKey || seen.has(dedupeKey)) continue;
    seen.add(dedupeKey);

    const normalizedSentence = normalizeInlineCitationText(sentence);
    const associated = citations.filter(citation => {
      if (!citation || !citation.label) return false;
      return normalizedSentence.includes(normalizeInlineCitationText(citation.label));
    });
    claims.push({
      id: `claim_${claims.length + 1}`,
      text: sentence,
      citations: associated,
      referenceIds: [...new Set(associated.flatMap(citation => citation.referenceIds || []))],
    });
    if (claims.length >= 20) break;
  }
  return claims;
}

function classifyClaim(claim) {
  if (!claim.citations.length) {
    return {
      status: 'UNVERIFIABLE',
      evidence: 'No associated citation was identified.',
      explanation: 'A possible factual statement was extracted, but no source citation could be mapped to it.',
      limitations: ['No citation was associated with this statement.', 'Scientific source evidence has not been retrieved for this report.'],
    };
  }
  return {
    status: 'UNVERIFIABLE',
    evidence: 'A citation marker was associated, but source passages have not yet been evaluated in this report.',
    explanation: 'The citation marker was identified. This extraction report does not determine whether the cited source supports the statement; use the research verification workflow for that assessment.',
    limitations: ['Citation identity and metadata may require confirmation.', 'No claim-support judgement is made during extraction.'],
  };
}

function buildReport(fileName, text) {
  const sourceText = String(text || '');
  const bodyText = removeReferenceSection(sourceText);
  const references = extractBibliographyReferences(sourceText);
  const citations = mapCitationsToReferences(extractCitations(bodyText), references);
  const claims = extractClaims(bodyText, citations).map(claim => {
    const result = classifyClaim(claim);
    const linkedReferences = references.filter(reference => claim.referenceIds.includes(reference.id));
    return {
      ...claim,
      ...result,
      source: claim.citations.length
        ? { title: linkedReferences[0]?.title || linkedReferences[0]?.raw || claim.citations[0].label, doi: linkedReferences[0]?.doi || null, retrieved: false, url: linkedReferences[0]?.doi ? `https://doi.org/${linkedReferences[0].doi}` : null }
        : null,
    };
  });

  const counts = claims.reduce((totals, claim) => {
    totals[claim.status] = (totals[claim.status] || 0) + 1;
    return totals;
  }, {});

  const summary = references.length
    ? `${claims.length} possible claims, ${citations.length} unique in-text citation markers and ${references.length} bibliography references detected. DOI values are shown when present in the bibliography; missing DOIs can be looked up from reference metadata during verification.`
    : `${claims.length} possible claims and ${citations.length} unique in-text citation markers detected. No structured bibliography section was recognized; source details may need to be supplied manually.`;

  return {
    fileName,
    summary: sourceText.trim() ? summary : 'No extractable text was found in the document.',
    extractedTextLength: sourceText.length,
    citations,
    references,
    claims,
    statistics: {
      totalClaims: claims.length,
      totalCitations: citations.length,
      totalReferences: references.length,
      referencesWithDoi: references.filter(reference => reference.doi).length,
      supported: counts.SUPPORTED || 0,
      partiallySupported: counts['PARTIALLY SUPPORTED'] || 0,
      unsupported: counts.UNSUPPORTED || 0,
      contradicted: counts.CONTRADICTED || 0,
      unverifiable: counts.UNVERIFIABLE || 0,
      mode: 'Rule-based claim extraction and bibliography mapping; source verification runs separately',
    },
  };
}

module.exports = {
  extractCitations,
  extractClaims,
  extractBibliographyReferences,
  mapCitationsToReferences,
  parseAuthorYearCitation,
  normalizeInlineCitationText,
  normalizeDoi,
  classifyClaim,
  buildReport,
};
