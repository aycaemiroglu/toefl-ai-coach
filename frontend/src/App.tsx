import { useState, FormEvent } from 'react'
import { TOEFL_PROMPTS } from './prompts'
import { evaluateEssay, EvaluateError, type EvaluateResponse, type StrengthWeaknessItem } from './lib/api'

const MIN_WORDS = 150

function wordCount(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0
}

function isDetailedItem(x: string | StrengthWeaknessItem): x is StrengthWeaknessItem {
  return typeof x === 'object' && x !== null && 'label' in x && 'explanation' in x
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    background: '#fff',
    padding: 24,
    borderRadius: 8,
    border: '1px solid #e0e0e0',
  },
  header: { marginBottom: 24 },
  title: { margin: 0, fontSize: '1.5rem', fontWeight: 600 },
  subtitle: { margin: '4px 0 0', fontSize: '0.9rem', color: '#555' },
  form: { display: 'flex', flexDirection: 'column', gap: 16 },
  label: { fontSize: '0.9rem', fontWeight: 600 },
  select: {
    padding: '8px 12px',
    fontSize: 16,
    border: '1px solid #ccc',
    borderRadius: 6,
    background: '#fff',
  },
  textarea: {
    padding: 12,
    fontSize: 16,
    lineHeight: 1.5,
    border: '1px solid #ccc',
    borderRadius: 6,
    resize: 'vertical',
    minHeight: 200,
    fontFamily: 'inherit',
  },
  wordCount: { fontSize: '0.85rem', color: '#666', marginTop: 4 },
  wordCountWarning: { fontSize: '0.85rem', color: '#b91c1c', marginTop: 4 },
  button: {
    padding: '10px 20px',
    fontSize: 16,
    fontWeight: 600,
    color: '#fff',
    background: '#2563eb',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    alignSelf: 'flex-start',
  },
  buttonDisabled: { opacity: 0.5, cursor: 'not-allowed' },
  error: {
    marginTop: 16,
    padding: 12,
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: 6,
    color: '#b91c1c',
    fontSize: '0.9rem',
  },
  result: { marginTop: 24, paddingTop: 24, borderTop: '1px solid #e0e0e0' },
  resultTitle: { margin: '0 0 8px', fontSize: '1.25rem', fontWeight: 600 },
  meta: { margin: '0 0 16px', fontSize: '0.85rem', color: '#555' },
  scoreBox: {
    marginBottom: 16,
    padding: 12,
    background: '#f8fafc',
    borderRadius: 6,
    border: '1px solid #e2e8f0',
  },
  scoreLabel: { fontSize: '0.85rem', color: '#64748b', marginBottom: 4 },
  scoreValue: { fontSize: '1.5rem', fontWeight: 700, color: '#0f172a' },
  rubricGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 12,
    marginBottom: 16,
  },
  rubricCard: {
    padding: 10,
    background: '#f8fafc',
    borderRadius: 6,
    border: '1px solid #e2e8f0',
  },
  rubricLabel: { fontSize: '0.75rem', color: '#64748b', marginBottom: 4 },
  rubricValue: { fontSize: '1.1rem', fontWeight: 600 },
  list: { margin: '0 0 16px', paddingLeft: 20 },
  listItem: { marginBottom: 4, fontSize: '0.95rem', lineHeight: 1.5 },
  sectionTitle: { margin: '0 0 8px', fontSize: '0.95rem', fontWeight: 600 },
  rewriteBox: {
    marginTop: 16,
    padding: 12,
    background: '#f0fdf4',
    border: '1px solid #bbf7d0',
    borderRadius: 6,
    fontSize: 15,
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap',
  },
}

type Status = 'idle' | 'loading' | 'success' | 'error'

const RUBRIC_LABELS: Record<keyof EvaluateResponse['subscores'], string> = {
  task_response: 'Task response',
  coherence_cohesion: 'Coherence & cohesion',
  lexical_resource: 'Lexical resource',
  grammar: 'Grammar',
}

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
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>TOEFL Writing Analyzer</h1>
        <p style={styles.subtitle}>AI feedback on Independent Writing</p>
      </header>

      <form onSubmit={handleSubmit} style={styles.form}>
        <label style={styles.label} htmlFor="prompt">
          Essay topic
        </label>
        <select
          id="prompt"
          value={promptId}
          onChange={(e) => setPromptId(e.target.value)}
          style={styles.select}
          disabled={loading}
        >
          {TOEFL_PROMPTS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.text}
            </option>
          ))}
        </select>

        <label style={styles.label} htmlFor="essay">
          Your essay
        </label>
        <textarea
          id="essay"
          value={essay}
          onChange={(e) => setEssay(e.target.value)}
          placeholder="Paste your essay here (about 250–300 words)…"
          rows={14}
          style={styles.textarea}
          disabled={loading}
        />
        <p style={meetsMinWords ? styles.wordCount : styles.wordCountWarning}>
          {words} word{words !== 1 ? 's' : ''}
          {!meetsMinWords && words > 0 && ` — at least ${MIN_WORDS} words required`}
        </p>

        <button
          type="submit"
          disabled={!canSubmit || loading}
          style={{
            ...styles.button,
            ...(!canSubmit || loading ? styles.buttonDisabled : {}),
          }}
        >
          {loading ? 'Analyzing…' : 'Analyze Essay'}
        </button>
      </form>

      {error && (
        <div style={styles.error} role="alert">
          {error}
        </div>
      )}

      {result && status === 'success' && (
        <section style={styles.result} aria-live="polite">
          <h2 style={styles.resultTitle}>Feedback</h2>
          <p style={styles.meta}>
            Model: {result.model} · {result.latency_ms} ms · {result.word_count} words
            {result.confidence && ` · Confidence: ${result.confidence.level}`}
          </p>

          <div style={styles.scoreBox}>
            <div style={styles.scoreLabel}>Overall score</div>
            <div style={styles.scoreValue}>
              {result.estimated_score.toFixed(1)} / 30
            </div>
          </div>

          <div style={styles.rubricGrid}>
            {(Object.keys(result.subscores) as Array<keyof EvaluateResponse['subscores']>).map(
              (key) => (
                <div key={key} style={styles.rubricCard}>
                  <div style={styles.rubricLabel}>{RUBRIC_LABELS[key]}</div>
                  <div style={styles.rubricValue}>
                    {result.subscores[key].toFixed(1)} / 5
                  </div>
                </div>
              )
            )}
          </div>

          <h3 style={styles.sectionTitle}>Strengths</h3>
          <ul style={styles.list}>
            {result.strengths.map((s, i) => (
              <li key={i} style={styles.listItem}>
                {isDetailedItem(s) ? (
                  <>
                    <strong>{s.label}</strong>: {s.explanation}
                    {s.evidence != null && s.evidence !== '' && (
                      <blockquote style={{ margin: '4px 0 0', fontSize: '0.9em', color: '#555' }}>
                        "{s.evidence}"
                      </blockquote>
                    )}
                  </>
                ) : (
                  String(s)
                )}
              </li>
            ))}
          </ul>

          <h3 style={styles.sectionTitle}>Weaknesses</h3>
          <ul style={styles.list}>
            {result.weaknesses.map((w, i) => (
              <li key={i} style={styles.listItem}>
                {isDetailedItem(w) ? (
                  <>
                    <strong>{w.label}</strong>: {w.explanation}
                    {w.evidence != null && w.evidence !== '' ? (
                      <blockquote style={{ margin: '4px 0 0', fontSize: '0.9em', color: '#555' }}>
                        "{w.evidence}"
                      </blockquote>
                    ) : (
                      <p style={{ margin: '4px 0 0', fontSize: '0.85em', color: '#888' }}>
                        No direct quote available{w.evidence_reason ? ` — ${w.evidence_reason}` : ''}
                      </p>
                    )}
                  </>
                ) : (
                  String(w)
                )}
              </li>
            ))}
          </ul>

          <h3 style={styles.sectionTitle}>Top 3 fixes</h3>
          <ol style={styles.list}>
            {result.top_fixes.map((f, i) => (
              <li key={i} style={styles.listItem}>
                {f}
              </li>
            ))}
          </ol>

          <h3 style={styles.sectionTitle}>Revised first paragraph</h3>
          <div style={styles.rewriteBox}>{result.rewrite_first_paragraph}</div>
        </section>
      )}
    </div>
  )
}
