import { useEffect, useRef, useState, type FormEvent } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, BarChart3, CheckCircle2, ChevronRight, CircleAlert, Download, FileText, LayoutDashboard, LogOut, Menu, Search, ShieldCheck, Upload, UserRound, X } from 'lucide-react'
import { getVerificationStatus, runVerification } from './services/verification'
import type { VerdictDecision, VerificationJobStatus } from './services/verification'
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
        <div className="document-card"><div className="document-top"><div><span className="file-icon"><FileText /></span><div><strong>Illustrative interface</strong><small>No document or evidence analyzed</small></div></div><span className="status-pill preview-pill">Preview only</span></div><div className="claim-line"><span>Example claim</span><strong>Claim result is unavailable until a source is retrieved.</strong></div><div className="evidence-card"><div className="evidence-score"><span>—</span><small>not scored</small></div><div><span className="supported-dot preview-status">Unverifiable</span><p>Source retrieval and evidence assessment are not implemented. No support conclusion is made.</p></div></div></div>
      </div>
    </div></section>
    <section id="how" className="process-section"><div className="cv-container"><div className="section-heading"><div><span className="section-kicker">The current workflow</span><h2>From PDF text to transparent limitations.</h2></div><p>Claim and citation extraction is available now. Source retrieval and scientific support assessment are not yet implemented.</p></div><div className="process-grid">{[
      ['01', 'Extract', 'Extract selectable PDF text and identify possible claims and in-text citations.'],
      ['02', 'Map', 'Associate a citation when it appears in the same extracted text line as a possible claim.'],
      ['03', 'Disclose', 'Report claims as unverifiable until source evidence can be retrieved and examined.'],
    ].map(item => <article key={item[0]}><span>{item[0]}</span><h3>{item[1]}</h3><p>{item[2]}</p></article>)}</div></div></section>
    <section id="features" className="features-section"><div className="cv-container feature-grid"><div><span className="section-kicker">Built for scrutiny</span><h2>See what extraction can—and cannot—show.</h2></div>{[
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
  ].map((stat, i) => <article className="stat-card" key={stat[0] as string}><div className={`stat-icon stat-${i}`}><FileText /></div><div><span>{stat[0]}</span><strong>{data ? stat[1] : '—'}</strong><small>{stat[2]}</small></div></article>)}</section>
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

  return <Shell><div className="page-header"><div><span className="page-kicker">Document analysis</span><h1>Upload a research document</h1><p>PDF only · Maximum 20 MB</p></div></div><div className="upload-layout"><section className="upload-card"><input ref={inputRef} type="file" accept=".pdf,application/pdf" hidden onChange={event => choose(event.target.files?.[0])} /><div className={`dropzone ${file ? 'has-file' : ''}`} role="button" tabIndex={0} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); inputRef.current?.click() } }} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); choose(event.dataTransfer.files[0]) }} onClick={() => inputRef.current?.click()}><div className="upload-icon">{file ? <CheckCircle2 /> : <Upload />}</div><h3>{file ? file.name : 'Drop your PDF here'}</h3><p>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · Ready to analyse` : 'or click to browse files'}</p>{!file && <span className="button button-outline">Choose PDF</span>}</div>{error && <div className="form-error"><CircleAlert size={16} />{error}</div>}{status && <div className="progress-block"><div><span>{status}</span><strong>{progress}%</strong></div><i><b style={{ width: `${progress}%` }} /></i></div>}<button className="button button-dark upload-button" disabled={!file || processing} onClick={submit}>{processing ? 'Processing...' : 'Start analysis'}<ArrowRight size={17} /></button></section><aside className="upload-aside"><h3>What happens next</h3>{['Extract PDF text', 'Identify possible claims', 'Find in-text citations', 'Report evidence limitations'].map((step, i) => <div key={step}><span>{i + 1}</span><p>{step}</p></div>)}</aside></div></Shell>
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
  const [startingVerification, setStartingVerification] = useState(false)
  useEffect(() => { if (id) getDocument(id).then(setDocument).catch(err => setError(err.message)) }, [id])
  if (error) return <Shell><div className="form-error">{error}</div></Shell>
  if (!document) return <Shell><div className="loading-state">Loading report...</div></Shell>
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

  async function startVerification() {
    if (!document) return
    const claim = document.report.claims[0]
    if (!claim) {
      setVerificationError('This report has no extracted claim to verify.')
      return
    }
    setVerificationError('')
    setStartingVerification(true)
    try {
      const job = await runVerification({
        claim_id: claim.id,
        claim_text: claim.text,
        citation_ids: claim.citations.map((citation, index) => citation.label || `citation_${index + 1}`),
        evidence: [],
        retrieval_status: 'not_found',
        source_limitations: ['No upstream document or research-evidence payload was supplied by the current frontend integration.'],
      })
      navigate(`/processing/${job.job_id}`)
    } catch (err) {
      setVerificationError((err as Error).message)
    } finally {
      setStartingVerification(false)
    }
  }
  return <Shell><div className="page-header report-header"><div><Link className="back-link" to="/dashboard">← Back to reports</Link><span className="page-kicker">Verification report</span><h1>{document.fileName}</h1><p>Processed {new Date(document.uploadedAt).toLocaleString()} · <b>{document.report.statistics.mode as string}</b></p>{downloadError && <div className="form-error">{downloadError}</div>}{verificationError && <div className="form-error">{verificationError}</div>}</div><div className="hero-actions"><button className="button button-outline" onClick={download}><Download size={17} />Download report</button><button className="button button-dark" disabled={startingVerification} onClick={startVerification}><ShieldCheck size={17} />{startingVerification ? 'Starting...' : 'Verify claim'}</button></div></div>
    <section className="report-summary"><div><span>Document summary</span><p>{document.report.summary}</p></div><div className="summary-stat"><strong>{document.report.claims.length}</strong><span>Claims found</span></div><div className="summary-stat"><strong>{document.report.citations.length}</strong><span>Citations found</span></div></section>
    <section className="report-card"><div className="card-heading"><div><h2>Possible claims</h2><p>Rule-based extraction only; this is not evidence verification</p></div><div className="filters">{['ALL', 'SUPPORTED', 'UNVERIFIABLE', 'UNSUPPORTED', 'CONTRADICTED', 'PARTIALLY SUPPORTED'].map(item => <button className={filter === item ? 'active' : ''} onClick={() => setFilter(item)} key={item}>{item === 'ALL' ? 'All' : item.charAt(0) + item.slice(1).toLowerCase()}</button>)}</div></div>{claims.length ? <div className="claim-list">{claims.map((claim, index) => <article className="claim-card" key={claim.id}><div className="claim-number">{String(index + 1).padStart(2, '0')}</div><div className="claim-content"><div className="claim-title"><h3>{claim.text}</h3><span className={`claim-status ${statusClass(claim.status)}`}>{claim.status}</span></div><div className="reason-grid"><div><span>Evidence availability</span><p>{claim.evidence}</p></div><div><span>Explanation</span><p>{claim.explanation}</p></div></div><div className="citation-row"><span>Citation</span>{claim.citations.length ? claim.citations.map(citation => <code key={citation.label}>{citation.label}</code>) : <code>No associated citation</code>}</div><div className="limitations"><strong>Limitations</strong><ul>{claim.limitations.map(limit => <li key={limit}>{limit}</li>)}</ul></div></div></article>)}</div> : <div className="empty-state"><h3>No matching claims</h3><p>This filter has no extracted claims.</p></div>}</section>
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
        <Link className="back-link" to="/dashboard">← Back to dashboard</Link>
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
      <div><Link className="back-link" to="/dashboard">← Back to workspace</Link><span className="page-kicker">Evidence viewer</span><h1>Research evidence</h1></div>
    </div>
    {!evidence ? <section className="dashboard-card"><div className="empty-state"><div><ShieldCheck /></div><h3>Evidence passage unavailable</h3><p>A Member 2 evidence response is not currently connected. No source or evidence passage is being fabricated.</p></div></section> :
      <div className="evidence-layout">
        <section className="dashboard-card evidence-claim"><div className="card-heading"><div><h2>Original claim</h2><p>Claim under review</p></div></div><div className="claim-list"><p>{claimText || 'Claim text was not provided by the navigation context.'}</p></div></section>
        <section className="dashboard-card"><div className="card-heading"><div><h2>{evidence.source_title || 'Research source'}</h2><p>Evidence passage {evidence.page_number ? `· Page ${evidence.page_number}` : ''}{evidence.section_name ? ` · ${evidence.section_name}` : ''}</p></div><span className="claim-status">{evidence.source_type || 'unknown'}</span></div><div className="claim-list"><blockquote className="evidence-passage">{evidence.text || 'No evidence text was returned.'}</blockquote><dl className="evidence-meta"><div><dt>Evidence ID</dt><dd>{evidence.evidence_id}</dd></div><div><dt>Source ID</dt><dd>{evidence.source_id}</dd></div>{evidence.retrieval_score !== null && evidence.retrieval_score !== undefined && <div><dt>Retrieval score</dt><dd>{evidence.retrieval_score}</dd></div>}</dl></div></section>
      </div>}
  </Shell>
}

function ProcessingPage() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<VerificationJobStatus | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!jobId) return
    let active = true

    async function poll() {
      try {
        const next = await getVerificationStatus(jobId as string)
        if (!active) return
        setStatus(next)
        if (next.status === 'completed' && next.result) {
          setError('')
          navigate('/verification-result', { replace: true, state: { result: next.result, jobId } })
        } else if (next.status === 'failed') {
          setError(next.error || 'Verification failed')
        }
      } catch (err) {
        if (active) setError((err as Error).message)
      }
    }

    void poll()
    const timer = window.setInterval(() => {
      if (status?.status !== 'completed' && status?.status !== 'failed') void poll()
    }, 2500)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [jobId, navigate, status?.status])

  const stages: { key: VerificationJobStatus['status']; label: string }[] = [
    { key: 'queued', label: 'Queued' },
    { key: 'running', label: 'Running' },
    { key: 'completed', label: 'Completed' },
    { key: 'failed', label: 'Failed' },
  ]
  const currentIndex = stages.findIndex(stage => stage.key === status?.status)

  return <Shell><div className="page-header"><div><span className="page-kicker">Verification job</span><h1>Processing claim</h1><p>Live status from the verification service.</p></div></div><section className="upload-layout"><article className="upload-card"><div className="loading-state">{error ? <div className="form-error"><CircleAlert size={16} />{error}</div> : <div className="processing-status"><span className={`processing-dot ${status?.status === 'running' ? 'running' : ''}`} /><p>{status?.status ? status.status.charAt(0).toUpperCase() + status.status.slice(1) : 'Queued'}</p><small>Job status is being checked against the backend.</small></div>}</div></article><aside className="upload-aside"><h3>Backend status</h3>{stages.map((stage, index) => <div className={index === currentIndex ? 'stage-current' : ''} key={stage.key}><span>{index + 1}</span><p>{stage.label}</p></div>)}</aside></section></Shell>
}

function VerificationResultPage() {
  const locationState = window.history.state?.usr as { result?: VerdictDecision; jobId?: string } | undefined
  const result = locationState?.result

  if (!result) {
    return <Shell><div className="empty-state"><h3>No verification result in this session</h3><p>Start verification from a report with a recognized claim.</p><Link className="button button-dark" to="/dashboard">Back to dashboard</Link></div></Shell>
  }

  const verdictClass = result.verdict.toLowerCase().replaceAll('_', '-')
  return <Shell><div className="page-header"><div><span className="page-kicker">Verification result</span><h1>Claim decision</h1><p>Job: {locationState?.jobId}</p></div><span className={`claim-status ${verdictClass}`}>{result.verdict}</span></div><section className="report-summary"><div><span>Explanation</span><p>{result.explanation}</p></div><div className="summary-stat"><strong>{result.evidence_strength}</strong><span>Evidence strength</span></div><div className="summary-stat"><strong>{result.human_review_required ? 'YES' : 'NO'}</strong><span>Human review</span></div></section><section className="report-card"><div className="card-heading"><div><h2>Evidence details</h2><p>Verification method: {result.method}</p></div></div><div className="claim-list"><article className="claim-card"><div className="claim-number">01</div><div className="claim-content"><div className="reason-grid"><div><span>Supporting evidence</span><p>{result.supporting_evidence_ids.length ? result.supporting_evidence_ids.join(', ') : 'No supporting evidence identified'}</p></div><div><span>Contradicting evidence</span><p>{result.contradicting_evidence_ids.length ? result.contradicting_evidence_ids.join(', ') : 'No contradicting evidence identified'}</p></div></div>{result.numerical_discrepancies.length > 0 && <div className="limitations"><strong>Numerical discrepancies</strong><ul>{result.numerical_discrepancies.map(item => <li key={`${item.claim_value}-${item.evidence_value}-${item.description}`}>{item.description}: {item.claim_value} / {item.evidence_value}{item.unit ? ` ${item.unit}` : ''}</li>)}</ul></div>}<div className="limitations"><strong>Limitations</strong>{result.limitations.length ? <ul>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul> : <p>None reported by the verification service.</p>}</div></div></article></div></section></Shell>
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
