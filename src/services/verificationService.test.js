const test = require('node:test');
const assert = require('node:assert/strict');

const { buildReport, extractCitations, extractClaims } = require('./verificationService');

test('extracts author-year citations and maps citations embedded in claims', () => {
  const text = 'Results demonstrate a measurable change in this hypothetical test scenario (Sample et al., 2021).';
  const citations = extractCitations(text);
  const claims = extractClaims(text, citations);

  assert.equal(citations.length, 1);
  assert.equal(citations[0].label, '(Sample et al., 2021)');
  assert.equal(claims.length, 1);
  assert.deepEqual(claims[0].citations.map(citation => citation.label), ['(Sample et al., 2021)']);
});

test('reports claims as unverifiable without retrieved evidence', () => {
  const report = buildReport('audit-fixture.pdf', 'Results demonstrate a measurable change in this hypothetical test scenario (Sample et al., 2021).');

  assert.equal(report.claims.length, 1);
  assert.equal(report.claims[0].status, 'UNVERIFIABLE');
  assert.equal(report.claims[0].source.retrieved, false);
  assert.equal('confidence' in report.claims[0], false);
  assert.equal(report.statistics.supported, 0);
  assert.match(report.statistics.mode, /no source verification/i);
});

test('does not infer claims from empty or short text', () => {
  const report = buildReport('empty.pdf', '');

  assert.equal(report.claims.length, 0);
  assert.equal(report.statistics.totalClaims, 0);
  assert.match(report.summary, /No extractable text/);
});
