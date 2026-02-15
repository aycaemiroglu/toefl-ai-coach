import { useState, FormEvent } from 'react'
import { TOEFL_PROMPTS } from './prompts'

const API_BASE = import.meta.env.VITE_API_URL || ''

export interface FeedbackResult {
  model?: string
  feedback: string
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    background: '#fff',
    padding: 24,
    borderRadius: 8,
    border: '1px solid #e0e0e0',
  },
  header: {
    marginBottom: 24,
  },
  title: {
    margin: 0,
    fontSize: '1.5rem',
    fontWeight: 600,
  },
  subtitle: {
    margin: '4px 0 0',
    fontSize: '0.9rem',
    color: '#555',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  label: {
    fontSize: '0.9rem',
    fontWeight: 600,
  },
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
  buttonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  error: {
    marginTop: 16,
    padding: 12,
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: 6,
    color: '#b91c1c',
    fontSize: '0.9rem',
  },
  result: {
    marginTop: 24,
    paddingTop: 24,
    borderTop: '1px solid #e0e0e0',
  },
  resultTitle: {
    margin: '0 0 8px',
    fontSize: '1.25rem',
    fontWeight: 600,
  },
  model: {
    margin: '0 0 12px',
    fontSize: '0.85rem',
    color: '#555',
  },
  feedback: {
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    fontSize: 15,
    lineHeight: 1.6,
  },
}

function getMockResult(): FeedbackResult {
  return {
    model: 'mock (backend not running)',
    feedback: `**Estimated score:** 24/30

**Strengths:**
- Clear thesis and position.
- Relevant examples to support your ideas.
- Logical flow with clear paragraphs.

**Weaknesses:**
- Some sentences could be more varied.
- Conclusion could briefly acknowledge the other side.

**Suggestions:**
1. Add one contrasting sentence before restating your view.
2. Use a relative clause to combine two short sentences.
3. Vary vocabulary (e.g. replace "clearly" with a more precise word).

Start your FastAPI backend on port 8000 to get real AI feedback.`,
  }
}

export default function App() {
  const [promptId, setPromptId] = useState('p01')
  const [essay, setEssay] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<FeedbackResult | null>(null)

  const selectedPrompt = TOEFL_PROMPTS.find((p) => p.id === promptId)?.text ?? ''
  const canSubmit = essay.trim().length > 0

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!canSubmit || loading) return

    setError(null)
    setResult(null)
    setLoading(true)

    try {
      if (!API_BASE) {
        await new Promise((r) => setTimeout(r, 600))
        setResult(getMockResult())
        return
      }

      const res = await fetch(`${API_BASE}/writing/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: selectedPrompt, essay: essay.trim() }),
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || `Request failed: ${res.status}`)
      }

      const data: FeedbackResult = await res.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
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

        <button
          type="submit"
          disabled={!canSubmit || loading}
          style={{
            ...styles.button,
            ...((!canSubmit || loading) ? styles.buttonDisabled : {}),
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

      {result && (
        <section style={styles.result} aria-live="polite">
          <h2 style={styles.resultTitle}>Feedback</h2>
          {result.model && (
            <p style={styles.model}>Model: {result.model}</p>
          )}
          <div style={styles.feedback}>
            {result.feedback}
          </div>
        </section>
      )}
    </div>
  )
}
