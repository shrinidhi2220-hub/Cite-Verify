import { useEffect, useRef, useState, type FormEvent } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, BarChart3, CheckCircle2, ChevronRight, CircleAlert, Download, FileText, LayoutDashboard, LogOut, Menu, Search, ShieldCheck, Upload, UserRound, X } from 'lucide-react'
import { getVerificationStatus, retryVerification } from './services/verification'
import type { VerdictDecision, VerificationJobStatus, ResearchSummary } from './services/verification'
import { runResearchVerification, type ResearchEvidenceRequest } from './services/retrieval'
import { login, register as registerAccount, clearSession, saveSession } from './services/auth'
import { getDashboard, getDocument, getDocuments, uploadDocument } from './services/documents'
import { downloadTextReport } from './services/reports'
import type { DashboardResponse, DocumentRecord, User } from './types/api'
import './App.css'

function Brand({ compact = false }: { compact?: boolean }) {
  return <Link className="brand" to="/"><span className="brand-mark"><ShieldCheck size={compact ? 19 : 22} /></span><span>Cite<span>Verify</span></span></Link>
}

function Header() {
  const [open, setOpen] = useState(false)
  return <header className="public-header"><div className="cv-container nav-wrap"><Brand /><nav className={open ? 'nav-open' : ''}><Link to="/#how">How it works</Link><Link to="/#features">Features</Link><Link to="/login">Sign in</Link><Link className="button button-dark button-sm" to="/register">Get started</Link></nav><button className="menu-button" onClick={() => setOpen(!open)} aria-label="Toggle navigation">{open ? <X /> : <Menu />}</button></div></header>
}

function Landing() {
  return <><Header /><main>
    <section className="hero-section"><div className="cv-container hero-grid">
      <div className="hero-copy"><div className="eyebrow"><span /> Evidence-first research review</div><h1>Know whether your <em>citations</em> hold up.</h1><p>CiteVerify extracts possible claims and citations from scientific PDFs, and clearly reports when evidence has not been retrieved for verification.</p><div className="hero-actions"><Link className="button button-dark" to="/register">Review a document <ArrowRight size={17} /></Link><a className="text-link" href="#how">See how it works <ChevronRight size={16} /></a></div><div className="trust-row"><span><CheckCircle2 /> Evidence-led</span><span><CheckCircle2 /> Claim-level results</span><span><CheckCircle2 /> Transparent limitations</span></div></div>
      <div className="hero-visual" aria-label="Verification preview">
        <div className="document-card"><div className="document-top"><div><span className="file-icon"><FileText /></span><div><strong>Illustrative interface</strong><small>No document or evidence analyzed</small></div></div><span className="status-pill preview-pill">Preview only</span></div><div className="claim-line"><span>Example claim</span><strong>Claim result is unavailable until a source is retrieved.</strong></div><div className="evidence-card"><div className="evidence-score"><span>â€”</span><small>not scored</small></div><div><span className="supported-dot preview-status">Unverifiable</span><p>Source retrieval and evidence assessment are not implemented. No support conclusion is made.</p></div></div></div>
      </div>
    </div></section>
    <section id="how" className="process-section"><div className="cv-container"><div className="section-heading"><div><span className="section-kicker">The current workflow</span><h2>From PDF text to transparent limitations.</h2></div><p>Claim and citation extraction is available now. Source retrieval and scientific support assessment are not yet implemented.</p></div><div className="process-grid">{[
      ['01', 'Extract', 'Extract selectable PDF text and identify possible claims and in-text citations.'],
      ['02', 'Map', 'Associate a citation when it appears in the same extracted text line as a possible claim.'],
      ['03', 'Disclose', 'Report claims as unverifiable until source evidence can be retrieved and examined.'],
    ].map(item => <article key={item[0]}><span>{item[0]}</span><h3>{item[1]}</h3><p>{item[2]}</p></article>)}</div></div></section>
    <section id="features" className="features-section"><div className="cv-container feature-grid"><div><span className="section-kicker">Built for scrutiny</span><h2>See what extraction canâ€”and cannotâ€”show.</h2></div>{[
      [Search, 'Claim extraction', 'Surface factual statements and distinguish them from broader discussion.'],
      [ShieldCheck, 'Honest classification', 'Use UNVERIFIABLE whenever evidence cannot be retrieved or examined.'],
      [BarChart3, 'Clear reporting', 'Review claim-level support, limitations and source details in one place.'],
    ].map(([Icon, title, text]) => { const I = Icon as typeof Search; return <article key={title as string}><I /><h3>{title as string}</h3><p>{text as string}</p></article> })}</div></section>
  </main><footer><div className="cv-container"><Brand /><p>Evidence-first citation verification.</p></div></footer></>
}

function AuthPage({ register = false }: { register?: boolean }) {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)
    const form = new FormData(event.currentTarget)
    try {
      const email = String(form.get('email'))
      const password = String(form.get('password'))
      const data = register
        ? await registerAccount(String(form.get('name')), email, password)
        : await login(email, password)
      saveSession(data)
      navigate('/dashboard')
    } catch (err) { setError((err as Error).message) } finally { setLoading(false) }
  }

  return <main className="auth-page"><div className="auth-brand"><Brand /></div><section className="auth-card"><div className="auth-heading"><span>{register ? 'Create your account' : 'Welcome back'}</span><h1>{register ? 'Start verifying.' : 'Sign in to CiteVerify.'}</h1><p>{register ? 'Build explainable, evidence-led research reports.' : 'Continue to your analysis workspace.'}</p></div><form onSubmit={submit}>{register && <label>Full name<input name="name" required placeholder="Alex Morgan" /></label>}<label>Email address<input name="email" type="email" required placeholder="you@university.edu" /></label><label>Password<input name="password" type="password" minLength={register ? 8 : 1} required placeholder={register ? 'At least 8 characters' : 'Enter password'} /></label>{error && <div className="form-error"><CircleAlert size={16} />{error}</div>}<button className="button button-dark auth-submit" disabled={loading}>{loading ? 'Please wait...' : register ? 'Create account' : 'Sign in'}<ArrowRight size={17} /></button></form><p className="auth-switch">{register ? 'Already have an account?' : 'New to CiteVerify?'} <Link to={register ? '/login' : '/register'}>{register ? 'Sign in' : 'Create account'}</Link></p></section></main>
}

function Protected({ children }: { children: React.ReactNode }) {
  return localStorage.getItem('cv_token') ? children : <Navigate to="/login" replace />
}

function Sidebar() {
  const navigate = useNavigate()
  function logout() { clearSession(); navigate('/login') }
  const user = JSON.parse(localStorage.getItem('cv_user') || '{"name":"Researcher"}') as User
  return <aside className="sidebar"><Brand compact /><nav><Link to="/dashboard"><LayoutDashboard />Dashboard</Link><Link to="/upload"><Upload />New analysis</Link><Link to="/profile"><UserRound />Profile</Link></nav><div className="sidebar-user"><span>{user.name?.slice(0, 1).toUpperCase()}</span><div><strong>{user.name}</strong><small>Research account</small></div><button onClick={logout} aria-label="Sign out"><LogOut /></button></div></aside>
}

function Shell({ children }: { children: React.ReactNode }) {
  const [mobile, setMobile] = useState(false)
  return <div className="app-shell"><div className={mobile ? 'sidebar-mobile open' : 'sidebar-mobile'}><Sidebar /></div><button className="shell-menu" onClick={() => setMobile(!mobile)} aria-label="Open menu">{mobile ? <X /> : <Menu />}</button><main className="app-main">{children}</main></div>
}

function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { getDashboard().then(setData).catch(err => setError(err.message)) }, [])
  const user = JSON.parse(localStorage.getItem('cv_user') || '{"name":"Researcher"}') as User
  return <Shell><div className="page-header"><div><span className="page-kicker">Workspace</span><h1>Good morning, {user.name?.split(' ')[0]}</h1><p>Track and review your scientific verification work.</p></div><Link className="button button-dark" to="/upload"><Upload size={17} />New analysis</Link></div>{error && <div className="form-error">{error}</div>}<section className="stat-grid">{[
    ['Documents', data?.totalDocuments || 0, 'Uploaded reports'],
    ['Claims analysed', data?.totalClaims || 0, 'Across all documents'],
    ['Supported', data?.supported || 0, 'No source verification performed'],
    ['Unverifiable', data?.unverifiable || 0, 'Source evidence unavailable'],
  ].map((stat, i) => <article className="stat-card" key={stat[0] as string}><div className={`stat-icon stat-${i}`}><FileText /></div><div><span>{stat[0]}</span><strong>{data ? stat[1] : 'â€”'}</strong><small>{stat[2]}</small></div></article>)}</section>
    <section className="dashboard-card"><div className="card-heading"><div><h2>Recent reports</h2><p>Latest document analyses</p></div><Link to="/profile">View all <ChevronRight size={15} /></Link></div>{!data && !error ? <div className="empty-state"><p>Loading reports...</p></div> : data?.recentDocuments.length ? <div className="report-table"><div className="table-head"><span>Document</span><span>Status</span><span>Claims</span><span>Updated</span><span /></div>{data.recentDocuments.map(doc => <Link className="table-row" to={`/reports/${doc.id}`} key={doc.id}><span className="document-name"><i><FileText /></i><strong>{doc.fileName}</strong></span><span><b className="status-pill status-ready">{doc.status}</b></span><span>{doc.report.claims.length}</span><span>{new Date(doc.uploadedAt).toLocaleDateString()}</span><ChevronRight /></Link>)}</div> : !error ? <div className="empty-state"><div><FileText /></div><h3>No reports yet</h3><p>Upload a PDF to begin your first claim-level extraction.</p><Link className="button button-dark" to="/upload">Upload document</Link></div> : null}</section></Shell>
}

function UploadPage() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [processing, setProcessing] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(0)

  async function submit() {
    if (!file) return
    setError('')
    setStatus('Uploading and extracting document text...')
    setProcessing(true)
    setProgress(0)
    try {
      const document = await uploadDocument(file, percent => setProgress(percent))
      if (document.id) setProgress(100)
      setStatus('Analysis complete')
      window.setTimeout(() => navigate(`/reports/${document.id}`), 350)
    } catch (err) { setError((err as Error).message); setStatus('') } finally { setProcessing(false) }
  }

  function choose(next?: File) {
    setError('')
    if (!next) return
    if (next.type !== 'application/pdf' && !next.name.toLowerCase().endsWith('.pdf')) {
      setFile(null)
      return setError('Only PDF files are accepted')
    }
    if (next.size > 20 * 1024 * 1024) {
      setFile(null)
      return setError('The PDF must be smaller than 20 MB')
    }
    setFile(next)
  }

  return <Shell><div className="page-header"><div><span className="page-kicker">Document analysis</span><h1>Upload a research document</h1><p>PDF only Â· Maximum 20 MB</p></div></div><div className="upload-layout"><section className="upload-card"><input ref={inputRef} type="file" accept=".pdf,application/pdf" hidden onChange={event => choose(event.target.files?.[0])} /><div className={`dropzone ${file ? 'has-file' : ''}`} role="button" tabIndex={0} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); inputRef.current?.click() } }} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); choose(event.dataTransfer.files[0]) }} onClick={() => inputRef.current?.click()}><div className="upload-icon">{file ? <CheckCircle2 /> : <Upload />}</div><h3>{file ? file.name : 'Drop your PDF here'}</h3><p>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB Â· Ready to analyse` : 'or click to browse files'}</p>{!file && <span className="button button-outline">Choose PDF</span>}</div>{error && <div className="form-error"><CircleAlert size={16} />{error}</div>}{status && <div className="progress-block"><div><span>{status}</span><strong>{progress}%</strong></div><i><b style={{ width: `${progress}%` }} /></i></div>}<button className="button button-dark upload-button" disabled={!file || processing} onClick={submit}>{processing ? 'Processing...' : 'Start analysis'}<ArrowRight size={17} /></button></section><aside className="upload-aside"><h3>What happens next</h3>{['Extract PDF text', 'Identify possible claims', 'Find in-text citations', 'Report evidence limitations'].map((step, i) => <div key={step}><span>{i + 1}</span><p>{step}</p></div>)}</aside></div></Shell>
}

const statusClass = (status: string) => status.toLowerCase().replaceAll(' ', '-')

function ReportPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [document, setDocument] = useState<DocumentRecord | null>(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('ALL')
  const [downloadError, setDownloadError] = useState('')
  const [verificationError, setVerificationError] = useState('')
  const [startingClaimId, setStartingClaimId] = useState<string | null>(null)
  const [editingClaimId, setEditingClaimId] = useState<string | null>(null)
  const [claimDrafts, setClaimDrafts] = useState<Record<string, string>>({})
  const [referenceSelections, setReferenceSelections] = useState<Record<string, string>>({})
  const [manualReferences, setManualReferences] = useState<Record<string, string>>({})

  useEffect(() => {
    if (id) getDocument(id).then(setDocument).catch(err => setError(err.message))
  }, [id])

  if (error) return <Shell><div className="form-error">{error}</div></Shell>
  if (!document) return <Shell><div className="loading-state">Loading report...</div></Shell>

  const allReferences = document.report.references || []
  const claims = document.report.claims.filter(claim => filter === 'ALL' || claim.status === filter)

  async function download() {
    if (!document) return
    setDownloadError('')
    try {
      await downloadTextReport(document.id, document.fileName)
    } catch (err) {
      setDownloadError((err as Error).message)
    }
  }

  function claimReferenceOptions(claim: DocumentRecord['report']['claims'][number]) {
    const linkedIds = new Set([
      ...(claim.referenceIds || []),
      ...claim.citations.flatMap(citation => citation.referenceIds || []),
    ])
    const linked = allReferences.filter(reference => linkedIds.has(reference.id))
    return linked.length ? linked : allReferences
  }

  async function startVerification(claim: DocumentRecord['report']['claims'][number]) {
    if (!document) return
    const referenceOptions = claimReferenceOptions(claim)
    const selectedReferenceId = referenceSelections[claim.id] || referenceOptions[0]?.id || ''
    const selectedReference = referenceOptions.find(reference => reference.id === selectedReferenceId)
    const manualReference = (manualReferences[claim.id] || '').trim()
    const referenceText = selectedReference
      ? (selectedReference.title || selectedReference.raw)
      : manualReference

    if (!referenceText && !selectedReference?.doi) {
      setVerificationError(`Choose a bibliography reference for ${claim.id}, or enter its paper title/DOI as a fallback.`)
      return
    }

    const claimText = (claimDrafts[claim.id] ?? claim.text)
      .replace(/\s*(?:--|—|–)\s*(?:page\s*)?\d+\s+of\s+\d+\s*$/i, '')
      .trim()

    if (!claimText) {
      setVerificationError('The claim text is empty. Edit the claim before verification.')
      return
    }

    setVerificationError('')
    setStartingClaimId(claim.id)
    try {
      const researchRequest: ResearchEvidenceRequest = {
        claim_id: claim.id,
        claim_text: claimText,
        citation_ids: claim.citations.map((citation, index) => citation.label || `citation_${index + 1}`),
        per_page: 5,
        top_k: 5,
        max_papers: 3,
      }

      const candidateDoi = selectedReference?.doi || ''
      const doiMatch = (candidateDoi || manualReference).match(/(?:https?:\/\/(?:dx\.)?doi\.org\/)?(10\.\d{4,9}\/[^\s]+)/i)
      const doi = doiMatch?.[1]?.replace(/[.,;)}\]]+$/, '')

      if (doi) {
        researchRequest.citation_doi = doi
        if (selectedReference?.title) researchRequest.citation_title = selectedReference.title
      } else {
        researchRequest.citation_title = referenceText
        researchRequest.search_query = referenceText
      }

      if (selectedReference?.authors?.length) researchRequest.citation_authors = selectedReference.authors
      if (selectedReference?.publicationYear) researchRequest.publication_year = selectedReference.publicationYear

      const job = await runResearchVerification(researchRequest)
      navigate(`/processing/${job.job_id}`)
    } catch (err) {
      setVerificationError((err as Error).message)
    } finally {
      setStartingClaimId(null)
    }
  }

  return <Shell>
    <div className="page-header report-header">
      <div>
        <Link className="back-link" to="/dashboard">← Back to reports</Link>
        <span className="page-kicker">Verification report</span>
        <h1>{document.fileName}</h1>
        <p>Processed {new Date(document.uploadedAt).toLocaleString()} · <b>{document.report.statistics.mode as string}</b></p>
        {downloadError && <div className="form-error">{downloadError}</div>}
        {verificationError && <div className="form-error">{verificationError}</div>}
      </div>
      <div className="hero-actions">
        <button className="button button-outline" onClick={download}><Download size={17} />Download report</button>
      </div>
    </div>

    <section className="report-summary">
      <div><span>Document summary</span><p>{document.report.summary}</p></div>
      <div className="summary-stat"><strong>{document.report.claims.length}</strong><span>Claims found</span></div>
      <div className="summary-stat"><strong>{document.report.citations.length}</strong><span>Citations found</span></div>
      <div className="summary-stat"><strong>{allReferences.length}</strong><span>References parsed</span></div>
    </section>

    <section className="report-card bibliography-card">
      <div className="card-heading">
        <div><h2>Detected bibliography</h2><p>DOIs are extracted directly when printed; otherwise title-based lookup runs automatically when you verify a linked claim.</p></div>
        <span className="bibliography-count">{allReferences.filter(reference => reference.doi).length} / {allReferences.length} DOI found</span>
      </div>
      {allReferences.length ? (
        <div className="bibliography-list">
          {allReferences.slice(0, 8).map(reference => (
            <article className="bibliography-item" key={reference.id}>
              <div className="bibliography-item-heading">
                <strong>{reference.label}</strong>
                <span className={`reference-status ${reference.doi ? 'resolved' : 'lookup'}`}>{reference.doi ? 'DOI detected' : reference.title ? 'Title lookup available' : 'Needs review'}</span>
              </div>
              <p>{reference.title || reference.raw}</p>
              <small>{reference.authors?.[0] ? `${reference.authors[0]} · ` : ''}{reference.publicationYear || 'Year not detected'}</small>
              {reference.doi && <code>DOI: {reference.doi}</code>}
            </article>
          ))}
          {allReferences.length > 8 && <p className="bibliography-more">Showing 8 of {allReferences.length} detected references. All parsed references remain available in the claim selectors.</p>}
        </div>
      ) : (
        <div className="research-empty">No structured bibliography section was detected in this PDF. You can still enter a paper title or DOI for an individual claim below.</div>
      )}
    </section>

    <section className="report-card">
      <div className="card-heading">
        <div><h2>Claim review</h2><p>Review and edit each extracted claim, confirm its reference, then verify it individually.</p></div>
        <div className="filters">{['ALL', 'SUPPORTED', 'UNVERIFIABLE', 'UNSUPPORTED', 'CONTRADICTED', 'PARTIALLY SUPPORTED'].map(item => <button className={filter === item ? 'active' : ''} onClick={() => setFilter(item)} key={item}>{item === 'ALL' ? 'All' : item.charAt(0) + item.slice(1).toLowerCase()}</button>)}</div>
      </div>
      {claims.length ? (
        <div className="claim-list">
          {claims.map((claim) => {
            const referenceOptions = claimReferenceOptions(claim)
            const linkedIds = new Set([...(claim.referenceIds || []), ...claim.citations.flatMap(citation => citation.referenceIds || [])])
            const hasDirectMapping = linkedIds.size > 0
            const selectedReferenceId = referenceSelections[claim.id] || (hasDirectMapping ? referenceOptions.find(reference => linkedIds.has(reference.id))?.id : '') || ''
            const selectedReference = referenceOptions.find(reference => reference.id === selectedReferenceId)
            const isEditing = editingClaimId === claim.id
            const currentText = claimDrafts[claim.id] ?? claim.text
            const displayNumber = String(document.report.claims.findIndex(item => item.id === claim.id) + 1).padStart(2, '0')

            return (
              <article className="claim-card claim-review-card" key={claim.id}>
                <div className="claim-number">{displayNumber}</div>
                <div className="claim-content">
                  <div className="claim-title">
                    <div><span className="claim-kind">POSSIBLE FACTUAL CLAIM · {claim.id.toUpperCase()}</span><h3>Claim statement</h3></div>
                    <span className={`claim-status ${statusClass(claim.status)}`}>{claim.status}</span>
                  </div>
                  {isEditing ? (
                    <textarea className="claim-editor" aria-label={`Edit ${claim.id}`} value={currentText} onChange={event => setClaimDrafts(previous => ({ ...previous, [claim.id]: event.target.value }))} rows={4} />
                  ) : (
                    <p className="claim-statement">{currentText}</p>
                  )}

                  <div className="claim-reference-panel">
                    <div className="claim-reference-heading"><strong>Source reference</strong><span>{claim.citations.length ? claim.citations.map(citation => citation.label).join(', ') : 'No inline citation mapped'}</span></div>
                    {referenceOptions.length > 0 ? (
                      <>
                        <label className="reference-select-label" htmlFor={`reference-${claim.id}`}>Bibliography entry</label>
                        <select id={`reference-${claim.id}`} value={selectedReferenceId} onChange={event => setReferenceSelections(previous => ({ ...previous, [claim.id]: event.target.value }))}>
                          <option value="">Choose the source for this claim</option>
                          {referenceOptions.map(reference => (
                            <option value={reference.id} key={reference.id}>{reference.label} · {(reference.title || reference.raw).slice(0, 105)}</option>
                          ))}
                        </select>
                        {selectedReference && (
                          <div className="selected-reference-details">
                            <strong>{selectedReference.title || selectedReference.raw}</strong>
                            <small>{selectedReference.authors?.[0] || 'Author not parsed'} · {selectedReference.publicationYear || 'Year not parsed'}</small>
                            {selectedReference.doi ? (
                              <code>DOI detected: {selectedReference.doi}</code>
                            ) : (
                              <small className="doi-lookup-note">No DOI printed in this reference. CiteVerify will search Crossref, OpenAlex and Semantic Scholar by the reference title and validate the metadata match during verification.</small>
                            )}
                          </div>
                        )}
                        {!hasDirectMapping && <small className="reference-warning">No automatic in-text citation-to-reference match was found for this claim. Please select the bibliography entry that supports it.</small>}
                      </>
                    ) : (
                      <div className="manual-reference-fallback">
                        <label className="reference-select-label" htmlFor={`manual-reference-${claim.id}`}>Paper title or DOI (fallback)</label>
                        <input id={`manual-reference-${claim.id}`} value={manualReferences[claim.id] || ''} onChange={event => setManualReferences(previous => ({ ...previous, [claim.id]: event.target.value }))} placeholder="Enter bibliography title or DOI" />
                        <small>Automatic DOI extraction was unavailable because no reference list could be parsed from this file.</small>
                      </div>
                    )}
                  </div>

                  <div className="claim-review-meta">
                    <span>{claim.citations.length} citation marker(s)</span>
                    <span>{claim.limitations.length} extraction limitation(s)</span>
                    <span>Not verified yet</span>
                  </div>
                  <div className="claim-review-actions">
                    {isEditing ? (
                      <>
                        <button className="button button-outline button-sm" onClick={() => setEditingClaimId(null)}>Done editing</button>
                        <button className="button button-outline button-sm" onClick={() => { setClaimDrafts(previous => { const next = { ...previous }; delete next[claim.id]; return next }); setEditingClaimId(null) }}>Discard edits</button>
                      </>
                    ) : (
                      <button className="button button-outline button-sm" onClick={() => setEditingClaimId(claim.id)}>Edit claim text</button>
                    )}
                    <button className="button button-dark button-sm" disabled={startingClaimId !== null || (!selectedReference && !manualReferences[claim.id]?.trim())} onClick={() => startVerification(claim)}>
                      <ShieldCheck size={16} />{startingClaimId === claim.id ? 'Starting verification...' : 'Verify this claim'}
                    </button>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      ) : (
        <div className="empty-state"><h3>No matching claims</h3><p>This filter has no extracted claims.</p></div>
      )}
    </section>
  </Shell>
}

function Profile() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => { getDocuments().then(data => setDocuments(data.documents)).catch(err => setError(err.message)).finally(() => setLoading(false)) }, [])
  const user = JSON.parse(localStorage.getItem('cv_user') || '{"name":"Researcher","email":""}') as User
  return <Shell><div className="page-header"><div><span className="page-kicker">Account</span><h1>Profile</h1><p>Account information and previous analyses.</p></div></div><section className="profile-grid"><article className="profile-card"><div className="avatar">{user.name?.slice(0, 1).toUpperCase()}</div><h2>{user.name}</h2><p>{user.email}</p><span className="status-pill">Active account</span></article><article className="profile-history"><div className="card-heading"><div><h2>Previous analyses</h2><p>{documents.length} total documents</p></div></div>{error ? <div className="form-error">{error}</div> : loading ? <div className="empty-state"><p>Loading analyses...</p></div> : documents.length ? documents.map(doc => <Link className="history-row" to={`/reports/${doc.id}`} key={doc.id}><span><i><FileText /></i><strong>{doc.fileName}</strong></span><small>{new Date(doc.uploadedAt).toLocaleDateString()}</small><ChevronRight /></Link>) : <div className="empty-state"><p>No previous analyses.</p></div>}</article></section></Shell>
}

function DocumentDetailsPage() {
  const { id } = useParams()
  const [document, setDocument] = useState<DocumentRecord | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (id) getDocument(id).then(setDocument).catch(err => setError(err.message))
  }, [id])

  if (error) return <Shell><div className="form-error">{error}</div></Shell>
  if (!document) return <Shell><div className="loading-state">Loading document...</div></Shell>

  return <Shell>
    <div className="page-header report-header">
      <div>
        <Link className="back-link" to="/dashboard">â† Back to dashboard</Link>
        <span className="page-kicker">Document overview</span>
        <h1>{document.fileName}</h1>
        <p>Uploaded {new Date(document.uploadedAt).toLocaleString()}</p>
      </div>
      <Link className="button button-outline" to={`/reports/${document.id}`}><FileText size={17} />Open report</Link>
    </div>
    <section className="stat-grid">
      <article className="stat-card"><div className="stat-icon"><FileText /></div><div><span>Status</span><strong className="stat-text-value">{document.status}</strong></div></article>
      <article className="stat-card"><div className="stat-icon"><Search /></div><div><span>Claims</span><strong>{document.report.claims.length}</strong></div></article>
      <article className="stat-card"><div className="stat-icon"><ShieldCheck /></div><div><span>Citations</span><strong>{document.report.citations.length}</strong></div></article>
      <article className="stat-card"><div className="stat-icon stat-3"><CircleAlert /></div><div><span>Requiring review</span><strong>{document.report.claims.filter(claim => claim.status === 'UNVERIFIABLE').length}</strong></div></article>
    </section>
    <section className="dashboard-card">
      <div className="card-heading"><div><h2>Extracted claims</h2><p>Claims and their associated citations</p></div></div>
      {document.report.claims.length ? <div className="claim-list">{document.report.claims.map((claim, index) =>
        <article className="claim-card" key={claim.id}>
          <div className="claim-number">{String(index + 1).padStart(2, '0')}</div>
          <div className="claim-content">
            <div className="claim-title"><h3>{claim.text}</h3><span className={`claim-status ${statusClass(claim.status)}`}>{claim.status}</span></div>
            <div className="citation-row"><span>Associated citations</span>{claim.citations.length ? claim.citations.map(citation => <code key={citation.label}>{citation.label}</code>) : <code>No associated citation</code>}</div>
            <div className="claim-actions"><Link className="text-link" to="/verification-result" state={{ claimText: claim.text }}>View verification details <ChevronRight size={15} /></Link></div>
          </div>
        </article>
      )}</div> : <div className="empty-state"><h3>No extracted claims</h3><p>The document did not yield any claims under the backend extraction rules.</p></div>}
    </section>
  </Shell>
}

function EvidenceViewerPage() {
  const locationState = window.history.state?.usr as { evidence?: import('./services/verification').EvidencePassage; claimText?: string; relation?: string } | undefined
  const evidence = locationState?.evidence
  const claimText = locationState?.claimText

  return <Shell>
    <div className="page-header report-header">
      <div><Link className="back-link" to="/dashboard">â† Back to workspace</Link><span className="page-kicker">Evidence viewer</span><h1>Research evidence</h1></div>
    </div>
    {!evidence ? <section className="dashboard-card"><div className="empty-state"><div><ShieldCheck /></div><h3>Evidence passage unavailable</h3><p>A Member 2 evidence response is not currently connected. No source or evidence passage is being fabricated.</p></div></section> :
      <div className="evidence-layout">
        <section className="dashboard-card evidence-claim"><div className="card-heading"><div><h2>Original claim</h2><p>Claim under review</p></div></div><div className="claim-list"><p>{claimText || 'Claim text was not provided by the navigation context.'}</p></div></section>
        <section className="dashboard-card"><div className="card-heading"><div><h2>{evidence.source_title || 'Research source'}</h2><p>Evidence passage {evidence.page_number ? `Â· Page ${evidence.page_number}` : ''}{evidence.section_name ? ` Â· ${evidence.section_name}` : ''}</p></div><span className="claim-status">{evidence.source_type || 'unknown'}</span></div><div className="claim-list"><blockquote className="evidence-passage">{evidence.text || 'No evidence text was returned.'}</blockquote><dl className="evidence-meta"><div><dt>Evidence ID</dt><dd>{evidence.evidence_id}</dd></div><div><dt>Source ID</dt><dd>{evidence.source_id}</dd></div>{evidence.retrieval_score !== null && evidence.retrieval_score !== undefined && <div><dt>Retrieval score</dt><dd>{evidence.retrieval_score}</dd></div>}</dl></div></section>
      </div>}
  </Shell>
}

function ProcessingPage() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<VerificationJobStatus | null>(null)
  const [error, setError] = useState('')
  const [retrying, setRetrying] = useState(false)

  useEffect(() => {
    if (!jobId) return

    let active = true
    let timer: number | undefined

    const poll = async () => {
      try {
        const next = await getVerificationStatus(jobId)
        if (!active) return

        setStatus(next)
        setError('')

        if (next.status === 'completed' && next.result) {
          navigate('/verification-result', {
            replace: true,
            state: {
              result: next.result,
              jobId,
              researchSummary: next.research_summary,
            },
          })
          return
        }

        // Terminal states stop the polling loop immediately.
        if (next.status === 'failed') {
          setError(next.error || 'Verification failed.')
          return
        }

        timer = window.setTimeout(poll, 2500)
      } catch (err) {
        if (!active) return
        const statusCode = (err as { status?: number }).status
        setError((err as Error).message || 'Unable to retrieve verification status.')

        // A missing job cannot become available by polling it repeatedly.
        if (statusCode === 404) return

        // Retry temporary network/server failures at a slower interval.
        timer = window.setTimeout(poll, 5000)
      }
    }

    void poll()
    return () => {
      active = false
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [jobId, navigate])

  async function retryAiAssessment() {
    if (!jobId || retrying) return
    setRetrying(true)
    setError('')
    try {
      const retryJob = await retryVerification(jobId)
      navigate(`/processing/${retryJob.job_id}`, { replace: true })
    } catch (err) {
      setError((err as Error).message || 'Unable to retry the AI assessment.')
    } finally {
      setRetrying(false)
    }
  }

  const stages: { key: VerificationJobStatus['stage']; label: string }[] = [
    { key: 'queued', label: 'Queued' },
    { key: 'research', label: 'Research retrieval' },
    { key: 'ai_reasoning', label: 'AI evidence assessment' },
    { key: 'completed', label: 'Completed' },
  ]
  const currentIndex = stages.findIndex(stage => stage.key === status?.stage)

  return <Shell>
    <div className="page-header">
      <div>
        <span className="page-kicker">Verification job</span>
        <h1>{status?.status === 'failed' ? 'Verification needs attention' : 'Processing claim'}</h1>
        <p>Job: {jobId}</p>
      </div>
      {status?.status === 'failed' && status.retry_available && (
        <button className="button button-dark" disabled={retrying} onClick={retryAiAssessment}>
          <ShieldCheck size={17} />{retrying ? 'Retrying...' : 'Retry AI assessment'}
        </button>
      )}
    </div>

    <section className="upload-layout">
      <article className="upload-card">
        <div className="loading-state">
          {error ? <div className="form-error"><CircleAlert size={16} />{error}</div> : (
            <div className="processing-status">
              <span className={`processing-dot ${status?.status === 'running' ? 'running' : ''}`} />
              <p>{status?.status ? status.status.charAt(0).toUpperCase() + status.status.slice(1) : 'Queued'}</p>
              <small>{status?.stage === 'research' ? 'Finding the cited research and extracting relevant passages.' : status?.stage === 'ai_reasoning' ? 'Assessing each retrieved passage against your claim.' : 'The job status is checked against the verification service.'}</small>
            </div>
          )}
          {status?.status === 'failed' && status.retry_available && (
            <p className="research-empty">Your retrieved research is saved. Retrying will reuse those passages and will not download the paper again.</p>
          )}
          {status?.status === 'failed' && !status.retry_available && (
            <p className="research-empty">No prepared evidence was saved for this job. A new research verification is required.</p>
          )}
        </div>
      </article>
      <aside className="upload-aside">
        <h3>Verification stages</h3>
        {stages.map((stage, index) => (
          <div className={index === currentIndex ? 'stage-current' : ''} key={stage.key}>
            <span>{index + 1}</span><p>{stage.label}</p>
          </div>
        ))}
      </aside>
    </section>

    {status?.research_summary && (
      <section className="report-card research-results">
        <div className="card-heading">
          <div>
            <h2>Saved research retrieval</h2>
            <p>{status.research_summary.citation_match_status} · {status.research_summary.retrieval_status} · {status.research_summary.evidence_count} usable passage(s)</p>
          </div>
        </div>
        {status.research_summary.papers.length > 0 && (
          <div className="research-paper-list">
            {status.research_summary.papers.map((paper, index) => (
              <article className="research-paper" key={`${paper.doi || paper.title}-${index}`}>
                <strong>{paper.title}</strong>
                <span>{paper.publication_year || 'Year not provided'}{paper.doi ? ` · DOI: ${paper.doi}` : ''}</span>
                <small>{paper.full_text_extracted ? 'Full text extracted' : paper.abstract_available ? 'Abstract available' : paper.pdf_status || 'No full text status'}</small>
              </article>
            ))}
          </div>
        )}
        {status.research_summary.evidence?.length ? (
          <div className="research-evidence-list">
            <h3>Preserved evidence passages</h3>
            {status.research_summary.evidence.map(passage => (
              <article className="research-evidence" key={passage.evidence_id}>
                <div>
                  <strong>{passage.source_title || 'Research source'}</strong>
                  <span>{passage.source_type || 'unknown'}{passage.page_number ? ` · Page ${passage.page_number}` : ''}{passage.section_name ? ` · ${passage.section_name}` : ''}</span>
                </div>
                <p>{passage.text}</p>
                <small>Evidence ID: {passage.evidence_id}</small>
              </article>
            ))}
          </div>
        ) : <p className="research-empty">No full-text or abstract evidence passage was saved for this job.</p>}
        {status.research_summary.source_limitations.length > 0 && (
          <div className="limitations">
            <strong>Retrieval limitations</strong>
            <ul>{status.research_summary.source_limitations.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul>
          </div>
        )}
      </section>
    )}
  </Shell>
}

function VerificationResultPage() {
  const locationState = window.history.state?.usr as { result?: VerdictDecision; jobId?: string; researchSummary?: ResearchSummary | null } | undefined
  const result = locationState?.result
  const researchSummary = locationState?.researchSummary

  if (!result) {
    return <Shell><div className="empty-state"><h3>No verification result in this session</h3><p>Start verification from a report with a recognized claim.</p><Link className="button button-dark" to="/dashboard">Back to dashboard</Link></div></Shell>
  }

  const verdictClass = result.verdict.toLowerCase().replaceAll('_', '-')
  return <Shell><div className="page-header"><div><span className="page-kicker">Verification result</span><h1>Claim decision</h1><p>Job: {locationState?.jobId}</p></div><span className={`claim-status ${verdictClass}`}>{result.verdict}</span></div><section className="report-summary"><div><span>Explanation</span><p>{result.explanation}</p></div><div className="summary-stat"><strong>{result.evidence_strength}</strong><span>Evidence strength</span></div><div className="summary-stat"><strong>{result.human_review_required ? 'YES' : 'NO'}</strong><span>Human review</span></div></section><section className="report-card"><div className="card-heading"><div><h2>Evidence details</h2><p>Verification method: {result.method}</p></div></div><div className="claim-list"><article className="claim-card"><div className="claim-number">01</div><div className="claim-content"><div className="reason-grid"><div><span>Supporting evidence</span><p>{result.supporting_evidence_ids.length ? result.supporting_evidence_ids.join(', ') : 'No supporting evidence identified'}</p></div><div><span>Contradicting evidence</span><p>{result.contradicting_evidence_ids.length ? result.contradicting_evidence_ids.join(', ') : 'No contradicting evidence identified'}</p></div></div>{result.numerical_discrepancies.length > 0 && <div className="limitations"><strong>Numerical discrepancies</strong><ul>{result.numerical_discrepancies.map(item => <li key={`${item.claim_value}-${item.evidence_value}-${item.description}`}>{item.description}: {item.claim_value} / {item.evidence_value}{item.unit ? ` ${item.unit}` : ''}</li>)}</ul></div>}<div className="limitations"><strong>Limitations</strong>{result.limitations.length ? <ul>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul> : <p>None reported by the verification service.</p>}</div></div></article></div></section>
    {researchSummary && <section className="report-card research-results"><div className="card-heading"><div><h2>Retrieved research and evidence</h2><p>{researchSummary.citation_match_status} Â· {researchSummary.retrieval_status} Â· {researchSummary.evidence_count} usable passage(s)</p></div></div>{researchSummary.papers.length > 0 && <div className="research-paper-list">{researchSummary.papers.map((paper, index) => <article className="research-paper" key={`${paper.doi || paper.title}-${index}`}><strong>{paper.title}</strong><span>{paper.publication_year || 'Year not provided'}{paper.doi ? ` Â· DOI: ${paper.doi}` : ''}</span><small>{paper.full_text_extracted ? 'Full text extracted' : paper.abstract_available ? 'Abstract available' : paper.pdf_status || 'No full text status'}</small></article>)}</div>}{researchSummary.evidence?.length ? <div className="research-evidence-list"><h3>Retrieved passages</h3>{researchSummary.evidence.map(passage => <article className="research-evidence" key={passage.evidence_id}><div><strong>{passage.source_title || 'Research source'}</strong><span>{passage.source_type || 'unknown'}{passage.page_number ? ` Â· Page ${passage.page_number}` : ''}{passage.section_name ? ` Â· ${passage.section_name}` : ''}</span></div><p>{passage.text}</p><small>Evidence ID: {passage.evidence_id} Â· Source ID: {passage.source_id}</small></article>)}</div> : <p className="research-empty">No claim-relevant full-text or abstract passage was retrieved. The verdict must be interpreted with this limitation.</p>}{researchSummary.source_limitations.length > 0 && <div className="limitations"><strong>Retrieval limitations</strong><ul>{researchSummary.source_limitations.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul></div>}</section>}
  </Shell>
}

export default function App() {
  return <BrowserRouter><Routes>
    <Route path="/" element={<Landing />} />
    <Route path="/login" element={<AuthPage />} />
    <Route path="/register" element={<AuthPage register />} />
    <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
    <Route path="/upload" element={<Protected><UploadPage /></Protected>} />
    <Route path="/documents/:id" element={<Protected><DocumentDetailsPage /></Protected>} />
    <Route path="/reports/:id" element={<Protected><ReportPage /></Protected>} />
    <Route path="/evidence" element={<Protected><EvidenceViewerPage /></Protected>} />
    <Route path="/profile" element={<Protected><Profile /></Protected>} />
    <Route path="/processing/:jobId" element={<Protected><ProcessingPage /></Protected>} />
    <Route path="/verification-result" element={<Protected><VerificationResultPage /></Protected>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></BrowserRouter>
}
