import { useState, FormEvent } from 'react'
import { TOEFL_PROMPTS } from './prompts'
import { evaluateEssay, EvaluateError, type EvaluateResponse } from './lib/api'

const MIN_WORDS = 120

function wordCount(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0
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
  confidenceBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 4,
    fontSize: '0.75rem',
    fontWeight: 600,
    marginLeft: 8,
  },
  confidenceBadgeHigh: { background: '#d1fae5', color: '#065f46' },
  confidenceBadgeMedium: { background: '#fef3c7', color: '#92400e' },
  confidenceBadgeLow: { background: '#fee2e2', color: '#991b1b' },
  confidenceNumeric: { fontSize: '0.75rem', color: '#64748b', marginTop: 4 },
  confidenceReasons: {
    marginTop: 8,
    padding: 8,
    background: '#f8fafc',
    borderRadius: 4,
    fontSize: '0.85rem',
  },
  confidenceReasonsTitle: { fontSize: '0.8rem', fontWeight: 600, marginBottom: 4, cursor: 'pointer' },
  confidenceReasonsList: { margin: 0, paddingLeft: 20, listStyle: 'disc' },
  calibrationBadge: {
    display: 'inline-block',
    padding: '2px 6px',
    borderRadius: 4,
    fontSize: '0.7rem',
    fontWeight: 600,
    background: '#e0e7ff',
    color: '#3730a3',
    marginLeft: 6,
    cursor: 'help',
    position: 'relative' as const,
  },
  calibrationNote: {
    marginTop: 4,
    fontSize: '0.8rem',
    color: '#64748b',
    fontStyle: 'italic',
  },
  lengthMessage: {
    marginTop: 6,
    fontSize: '0.85rem',
    color: '#475569',
    padding: '4px 8px',
    background: '#f1f5f9',
    borderRadius: 4,
    borderLeft: '3px solid #94a3b8',
  },
}

type Status = 'idle' | 'loading' | 'success' | 'error'

const RUBRIC_LABELS: Record<keyof EvaluateResponse['rubric'], string> = {
  task_response: 'Task response',
  coherence: 'Coherence & cohesion',
  lexical: 'Lexical resource',
  grammar: 'Grammar',
}

export default function App() {
  const [promptId, setPromptId] = useState('p01')
  const [essay, setEssay] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<EvaluateResponse | null>(null)
  const [showConfidenceReasons, setShowConfidenceReasons] = useState(false)

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
            Model: {result.model_name} · {result.timestamps.latency_ms} ms · {result.text_stats.word_count} words · {result.text_stats.sentence_count} sentences
          </p>

          <div style={styles.scoreBox}>
            <div style={styles.scoreLabel}>Overall score</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <div style={styles.scoreValue}>
                {result.scoring.final.toFixed(1)} / 30
              </div>
              {result.scoring.length_penalty < 1 && (
                <span
                  style={styles.calibrationBadge}
                  title={`Raw: ${result.scoring.raw.toFixed(1)} · Penalty: ${result.scoring.length_penalty.toFixed(2)} · Final: ${result.scoring.final.toFixed(1)}`}
                >
                  Calibrated
                </span>
              )}
              {result.confidence && (
                <span
                  style={{
                    ...styles.confidenceBadge,
                    ...(result.confidence.level === 'High'
                      ? styles.confidenceBadgeHigh
                      : result.confidence.level === 'Medium'
                        ? styles.confidenceBadgeMedium
                        : styles.confidenceBadgeLow),
                  }}
                >
                  {result.confidence.level}
                </span>
              )}
            </div>
            {result.scoring.length_penalty < 1 && (
              <div style={styles.calibrationNote}>
                Shorter than recommended length; score reduced. (Raw: {result.scoring.raw.toFixed(1)}, x{result.scoring.length_penalty.toFixed(2)})
              </div>
            )}
            {result.length && (
              <div style={styles.lengthMessage}>
                {result.length.message}
              </div>
            )}
            {result.confidence && (
              <>
                <div style={styles.confidenceNumeric}>
                  Confidence: {result.confidence.score}/100
                </div>
                {result.confidence.reasons && result.confidence.reasons.length > 0 && (
                  <div style={styles.confidenceReasons}>
                    <div
                      style={styles.confidenceReasonsTitle}
                      onClick={() => setShowConfidenceReasons(!showConfidenceReasons)}
                    >
                      {showConfidenceReasons ? '▼' : '▶'} Why {result.confidence.level}?
                    </div>
                    {showConfidenceReasons && (
                      <ul style={styles.confidenceReasonsList}>
                        {result.confidence.reasons.map((r, i) => (
                          <li key={i} style={{ marginBottom: 4 }}>
                            {r}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          <div style={styles.rubricGrid}>
            {(Object.keys(result.rubric) as Array<keyof EvaluateResponse['rubric']>).map(
              (key) => (
                <div key={key} style={styles.rubricCard}>
                  <div style={styles.rubricLabel}>{RUBRIC_LABELS[key]}</div>
                  <div style={styles.rubricValue}>
                    {result.rubric[key].toFixed(1)} / 5
                  </div>
                </div>
              )
            )}
          </div>

          <h3 style={styles.sectionTitle}>Strengths</h3>
          <ul style={styles.list}>
            {result.evidence.strengths.map((s, i) => (
              <li key={i} style={styles.listItem}>
                <strong>{s.label}</strong>: {s.explanation}
                {s.evidence != null && s.evidence !== '' && (
                  <blockquote style={{ margin: '4px 0 0', fontSize: '0.9em', color: '#555' }}>
                    &ldquo;{s.evidence}&rdquo;
                  </blockquote>
                )}
              </li>
            ))}
          </ul>

          <h3 style={styles.sectionTitle}>Weaknesses</h3>
          <ul style={styles.list}>
            {result.evidence.weaknesses.map((w, i) => (
              <li key={i} style={styles.listItem}>
                <strong>{w.label}</strong>: {w.explanation}
                {w.evidence != null && w.evidence !== '' ? (
                  <blockquote style={{ margin: '4px 0 0', fontSize: '0.9em', color: '#555' }}>
                    &ldquo;{w.evidence}&rdquo;
                  </blockquote>
                ) : (
                  <p style={{ margin: '4px 0 0', fontSize: '0.85em', color: '#888' }}>
                    No direct quote available{w.evidence_fallback ? ` — ${w.evidence_fallback}` : ''}
                  </p>
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
