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

test('extracts the Transformer factual claim and maps its numbered citation from flattened PDF text', () => {
  const text = 'CiteVerify - Scientific Test Document Claim to verify The Transformer architecture relies entirely on attention mechanisms and dispenses with recurrence and convolutions [1]. References [1] Vaswani, A. et al. (2017). Attention Is All You Need. Advances in Neural Information Processing Systems 30. DOI: 10.48550/arXiv.1706.03762';
  const citations = extractCitations(text);
  const claims = extractClaims(text, citations);

  assert.equal(claims.length, 1);
  assert.equal(
    claims[0].text,
    'The Transformer architecture relies entirely on attention mechanisms and dispenses with recurrence and convolutions [1].',
  );
  assert.deepEqual(claims[0].citations.map(citation => citation.label), ['[1]']);
});

test('does not extract declarations, recommendations, cyber-safety instructions or UI demo commands', () => {
  const text = [
    'We affirm that this activity and report are the results of our own effort and have not been copied or reproduced from any source.',
    'Set a daily plan for study, entertainment and rest.',
    'If you experience or witness cyberbullying, save relevant evidence and report it.',
    'DURING STUDY Keep notifications off and take short movement breaks.',
    'Complete checkout. Show order confirmation and an order summary to the customer.',
    'Open a verified review, then show opt-in customer details after authentication.',
  ].join(' ');

  assert.deepEqual(extractClaims(text, extractCitations(text)), []);
});

test('removes duplicate factual statements even when punctuation differs', () => {
  const text = [
    'The Transformer architecture relies entirely on attention mechanisms and dispenses with recurrence and convolutions [1].',
    'The Transformer architecture relies entirely on attention mechanisms and dispenses with recurrence and convolutions [1]',
  ].join(' ');

  const claims = extractClaims(text, extractCitations(text));
  assert.equal(claims.length, 1);
});

test('does not treat the bibliography entry itself as a claim', () => {
  const text = 'The Transformer architecture relies entirely on attention mechanisms and dispenses with recurrence and convolutions [1].\nReferences\n[1] Vaswani, A. et al. (2017). Attention Is All You Need. Advances in Neural Information Processing Systems 30.';
  const claims = extractClaims(text, extractCitations(text));

  assert.equal(claims.length, 1);
  assert.match(claims[0].text, /^The Transformer architecture/);
});

test('reports extracted claims as unverifiable until source evidence is evaluated', () => {
  const report = buildReport(
    'audit-fixture.pdf',
    'Results demonstrate a measurable change in this hypothetical test scenario (Sample et al., 2021).',
  );

  assert.equal(report.claims.length, 1);
  assert.equal(report.claims[0].status, 'UNVERIFIABLE');
  assert.equal(report.claims[0].source.retrieved, false);
  assert.equal('confidence' in report.claims[0], false);
  assert.equal(report.statistics.supported, 0);
  assert.match(report.statistics.mode, /source verification runs separately/i);
});

test('does not infer claims from empty or short text', () => {
  const report = buildReport('empty.pdf', '');

  assert.equal(report.claims.length, 0);
  assert.equal(report.statistics.totalClaims, 0);
  assert.match(report.summary, /No extractable text/);
});


test('removes a PDF page counter appended to an extracted claim', () => {
  const text = 'The Transformer architecture relies entirely on attention mechanisms and dispenses with recurrence and convolutions. -- 1 of 1';
  const claims = extractClaims(text, []);

  assert.equal(claims.length, 1);
  assert.equal(
    claims[0].text,
    'The Transformer architecture relies entirely on attention mechanisms and dispenses with recurrence and convolutions.',
  );
  assert.doesNotMatch(claims[0].text, /1 of 1/);
});

test('removes a Page X of Y suffix from an extracted claim', () => {
  const text = 'The Transformer architecture relies entirely on attention mechanisms and dispenses with recurrence and convolutions. — Page 1 of 3';
  const claims = extractClaims(text, []);

  assert.equal(claims.length, 1);
  assert.equal(
    claims[0].text,
    'The Transformer architecture relies entirely on attention mechanisms and dispenses with recurrence and convolutions.',
  );
});

test('extracts bibliography DOI and maps numbered in-text citation to the full reference', () => {
  const text = [
    'The Transformer architecture relies entirely on attention mechanisms and dispenses with recurrence and convolutions [1].',
    'References',
    '[1] Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, and Illia Polosukhin. Attention Is All You Need. Advances in Neural Information Processing Systems, 2017. https://doi.org/10.48550/arXiv.1706.03762',
  ].join('\n');
  const report = buildReport('transformer.pdf', text);

  assert.equal(report.references.length, 1);
  assert.equal(report.references[0].title, 'Attention Is All You Need');
  assert.equal(report.references[0].doi, '10.48550/arXiv.1706.03762');
  assert.deepEqual(report.claims[0].referenceIds, ['ref_1']);
  assert.equal(report.claims[0].source.doi, '10.48550/arXiv.1706.03762');
});

test('keeps bibliography references without DOI available for automatic title lookup', () => {
  const text = [
    'The model achieved improved performance across the benchmark evaluation [1].',
    'References',
    '[1] Smith, J. (2021). A Detailed Study of Benchmark Model Performance. Journal of Research Methods, 4(2), 10-20.',
  ].join('\n');
  const report = buildReport('benchmark.pdf', text);

  assert.equal(report.references.length, 1);
  assert.equal(report.references[0].title, 'A Detailed Study of Benchmark Model Performance');
  assert.equal(report.references[0].doi, null);
  assert.equal(report.references[0].doiStatus, 'TITLE_LOOKUP_REQUIRED');
  assert.deepEqual(report.claims[0].referenceIds, ['ref_1']);
});

test('splits grouped author-year citations and maps each author-year to the matching bibliography entry', () => {
  const text = [
    'Unlike recent language representation models (Peters et al., 2018a; Radford et al., 2018), BERT is designed to pretrain deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.',
    'References',
    'Akbik, A., Blythe, D. and Vollgraf, B. (2018). Contextual string embeddings for sequence labeling. In Proceedings of NAACL.',
    'Peters, M. E., Neumann, M., Iyyer, M., Gardner, M., Clark, C., Lee, K. and Zettlemoyer, L. (2018a). Deep contextualized word representations. In Proceedings of NAACL.',
    'Radford, A., Narasimhan, K., Salimans, T. and Sutskever, I. (2018). Improving language understanding by generative pre-training. OpenAI.',
  ].join('\n');

  const report = buildReport('bert-author-year.pdf', text);
  const claim = report.claims[0];

  assert.equal(report.references.length, 3);
  assert.equal(claim.citations.length, 2);
  assert.deepEqual(claim.referenceIds, ['ref_2', 'ref_3']);
  assert.deepEqual(claim.citations.map(item => item.referenceIds), [['ref_2'], ['ref_3']]);
});

test('maps narrative author-year citations such as Peters et al. (2018a)', () => {
  const text = [
    'Peters et al. (2018a) demonstrate contextual representations that improve language understanding in several tasks.',
    'References',
    'Peters, M. E., Neumann, M., Iyyer, M., Gardner, M., Clark, C., Lee, K. and Zettlemoyer, L. (2018a). Deep contextualized word representations. In Proceedings of NAACL.',
  ].join('\n');

  const report = buildReport('bert-narrative-citation.pdf', text);
  assert.equal(report.claims.length, 1);
  assert.equal(report.claims[0].citations.length, 1);
  assert.deepEqual(report.claims[0].referenceIds, ['ref_1']);
});

test('matches author-year citations despite PDF whitespace and unicode dash normalization', () => {
  const text = [
    'The research compares earlier language models (Peters et al., 2018a; Radford et al., 2018) and describes their differences in the full model discussion.',
    'References',
    'Peters, M. E., Neumann, M., Iyyer, M., Gardner, M., Clark, C., Lee, K. and Zettlemoyer, L. (2018a). Deep contextualized word representations. In Proceedings of NAACL.',
    'Radford, A., Narasimhan, K., Salimans, T. and Sutskever, I. (2018). Improving language understanding by generative pre-training. OpenAI.',
  ].join('\n');

  const report = buildReport('bert-whitespace.pdf', text);
  assert.equal(report.claims.length, 1);
  assert.equal(report.claims[0].citations.length, 2);
  assert.deepEqual(report.claims[0].referenceIds, ['ref_1', 'ref_2']);
});
