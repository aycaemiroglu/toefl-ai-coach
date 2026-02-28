import { useState, FormEvent } from 'react'
import { TOEFL_PROMPTS } from './prompts'
import { evaluateEssay, EvaluateError, type EvaluateResponse } from './lib/api'
import ScoreCard from './components/ScoreCard'
import ConfidenceCard from './components/ConfidenceCard'
import RubricGrid from './components/RubricGrid'
import EvidenceSection from './components/EvidenceSection'
import DebugPanel from './components/DebugPanel'

const MIN_WORDS = 120

function wordCount(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0
}

type Status = 'idle' | 'loading' | 'success' | 'error'

export default function App() {
  const [promptId, setPromptId] = useState('p01')
  const [essay, setEssay] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<EvaluateResponse | null>(null)

  const selectedPrompt = TOEFL_PROMPTS.find((p) => p.id === promptId)?.text ?? ''
  const words = wordCount(essay)
  const meetsMinWords = words >= MIN_WORDS
  const canSubmit = essay.trim().length > 0 && meetsMinWords
  const loading = status === 'loading'

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!canSubmit || loading) return
    setError(null)
    setResult(null)
    setStatus('loading')
    try {
      const data = await evaluateEssay({ prompt: selectedPrompt, essay: essay.trim() })
      setResult(data)
      setStatus('success')
    } catch (err) {
      const message =
        err instanceof EvaluateError
          ? err.detail ?? err.message
          : err instanceof Error
            ? err.message
            : 'Request failed'
      setError(message)
      setStatus('error')
    }
  }

  return (
    <div style={s.page}>
      {/* Header */}
      <header style={s.header}>
        <h1 style={s.title}>TOEFL Writing Analyzer</h1>
        <p style={s.subtitle}>AI-powered feedback on Independent Writing</p>
      </header>

      {/* Form */}
      <form onSubmit={handleSubmit} style={s.form}>
        <label style={s.formLabel} htmlFor="prompt">Essay topic</label>
        <select
          id="prompt"
          value={promptId}
          onChange={(e) => setPromptId(e.target.value)}
          style={s.select}
          disabled={loading}
        >
          {TOEFL_PROMPTS.map((p) => (
            <option key={p.id} value={p.id}>{p.text}</option>
          ))}
        </select>

        <label style={s.formLabel} htmlFor="essay">Your essay</label>
        <textarea
          id="essay"
          value={essay}
          onChange={(e) => setEssay(e.target.value)}
          placeholder="Paste your essay here (about 250-300 words)..."
          rows={14}
          style={s.textarea}
          disabled={loading}
        />
        <p style={meetsMinWords ? s.wordCount : s.wordCountWarn}>
          {words} word{words !== 1 ? 's' : ''}
          {!meetsMinWords && words > 0 && ` \u2014 at least ${MIN_WORDS} words required`}
        </p>

        <button
          type="submit"
          disabled={!canSubmit || loading}
          style={{ ...s.button, ...(!canSubmit || loading ? s.buttonOff : {}) }}
        >
          {loading ? 'Analyzing\u2026' : 'Analyze Essay'}
        </button>
      </form>

      {/* Error */}
      {error && <div style={s.error} role="alert">{error}</div>}

      {/* Results pipeline */}
      {result && status === 'success' && (
        <section style={s.results} aria-live="polite">
          <div style={s.pipelineLabel}>Evaluation Pipeline</div>

          {/* Step 1 + 2: Score and Confidence side by side */}
          <div style={s.topRow}>
            <div style={s.topCard}><ScoreCard scoring={result.scoring} length={result.length} /></div>
            <div style={s.topCard}><ConfidenceCard confidence={result.confidence} /></div>
          </div>

          {/* Step 3: Rubric */}
          <RubricGrid rubric={result.rubric} />

          {/* Step 4: Evidence */}
          <EvidenceSection evidence={result.evidence} />

          {/* Step 5: Top fixes */}
          <div style={s.fixesCard}>
            <h3 style={s.sectionLabel}>Top 3 Fixes</h3>
            <ol style={s.fixesList}>
              {result.top_fixes.map((f, i) => (
                <li key={i} style={s.fixItem}>{f}</li>
              ))}
            </ol>
          </div>

          {/* Step 6: Rewrite */}
          <div style={s.rewriteCard}>
            <h3 style={s.sectionLabel}>Revised First Paragraph</h3>
            <div style={s.rewriteText}>{result.rewrite_first_paragraph}</div>
          </div>

          {/* Debug (dev only) */}
          <DebugPanel result={result} />

          {/* Meta footer */}
          <div style={s.meta}>
            {result.model_name} &middot; {result.timestamps.latency_ms}ms &middot; {result.text_stats.word_count} words &middot; {result.text_stats.sentence_count} sentences
          </div>
        </section>
      )}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  page: {
    background: '#fff',
    padding: 28,
    borderRadius: 16,
    border: '1px solid #e2e8f0',
    boxShadow: '0 4px 12px rgba(0,0,0,0.04)',
  },
  header: { marginBottom: 24 },
  title: { margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#0f172a' },
  subtitle: { margin: '4px 0 0', fontSize: '0.9rem', color: '#64748b' },

  form: { display: 'flex', flexDirection: 'column', gap: 12 },
  formLabel: { fontSize: '0.85rem', fontWeight: 600, color: '#334155' },
  select: {
    padding: '8px 12px',
    fontSize: 15,
    border: '1px solid #cbd5e1',
    borderRadius: 8,
    background: '#fff',
    color: '#0f172a',
  },
  textarea: {
    padding: 14,
    fontSize: 15,
    lineHeight: 1.6,
    border: '1px solid #cbd5e1',
    borderRadius: 8,
    resize: 'vertical',
    minHeight: 200,
    fontFamily: 'inherit',
    color: '#0f172a',
  },
  wordCount: { fontSize: '0.82rem', color: '#64748b', margin: '2px 0 0' },
  wordCountWarn: { fontSize: '0.82rem', color: '#dc2626', margin: '2px 0 0' },
  button: {
    padding: '10px 24px',
    fontSize: 15,
    fontWeight: 600,
    color: '#fff',
    background: '#2563eb',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    alignSelf: 'flex-start',
    transition: 'background 0.15s',
  },
  buttonOff: { opacity: 0.5, cursor: 'not-allowed' },
  error: {
    marginTop: 16,
    padding: 12,
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: 8,
    color: '#dc2626',
    fontSize: '0.88rem',
  },

  results: {
    marginTop: 28,
    paddingTop: 24,
    borderTop: '2px solid #e2e8f0',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  pipelineLabel: {
    fontSize: '0.75rem',
    fontWeight: 700,
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    marginBottom: -4,
  },
  topRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
  },
  topCard: {},

  sectionLabel: {
    margin: '0 0 10px',
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },

  fixesCard: {
    padding: '16px 18px',
    background: '#fff',
    borderRadius: 12,
    border: '1px solid #e2e8f0',
    boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  },
  fixesList: { margin: 0, paddingLeft: 22 },
  fixItem: { fontSize: '0.88rem', color: '#334155', marginBottom: 6, lineHeight: 1.5 },

  rewriteCard: {
    padding: '16px 18px',
    background: '#f0fdf4',
    borderRadius: 12,
    border: '1px solid #bbf7d0',
  },
  rewriteText: {
    fontSize: '0.88rem',
    lineHeight: 1.7,
    color: '#1e293b',
    whiteSpace: 'pre-wrap',
  },

  meta: {
    textAlign: 'center',
    fontSize: '0.75rem',
    color: '#94a3b8',
    paddingTop: 8,
  },
}
