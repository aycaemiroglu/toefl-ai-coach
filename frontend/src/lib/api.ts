/**
 * API client for TOEFL essay evaluation.
 * Backend: POST /api/evaluate (proxied to localhost:8000 in dev).
 */

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export interface EvaluatePayload {
  prompt: string
  essay: string
  prompt_id?: string
}

// --- New unified contract types ---

export interface TextStats {
  word_count: number
  sentence_count: number
}

export interface Rubric {
  task_response: number
  coherence: number
  lexical: number
  grammar: number
}

export interface Scoring {
  raw: number
  length_penalty: number
  final: number
}

export interface ConfidenceSignals {
  word_count: number
  subscore_variance: number
  weakness_count: number
  has_counterargument_weakness: boolean
  confidence_before_clamp: number
  confidence_after_clamp: number
}

export interface Confidence {
  level: 'Low' | 'Medium' | 'High'
  score: number
  reasons: string[]
  signals: ConfidenceSignals
}

export interface Timestamps {
  received_at: string
  completed_at: string
  latency_ms: number
}

export interface LengthEvaluation {
  tier: 'short' | 'recommended' | 'ideal'
  message: string
}

export interface StrengthItem {
  label: string
  explanation: string
  evidence: string | null
}

export interface WeaknessItem {
  label: string
  explanation: string
  evidence: string | null
  evidence_fallback?: string | null
}

export interface Evidence {
  strengths: StrengthItem[]
  weaknesses: WeaknessItem[]
}

export interface EvaluateResponse {
  request_id: string
  prompt_id: string | null
  model_name: string
  overall_score: number
  timestamps: Timestamps
  text_stats: TextStats
  rubric: Rubric
  scoring: Scoring
  confidence: Confidence
  length: LengthEvaluation
  evidence: Evidence
  top_fixes: string[]
  rewrite_first_paragraph: string
}

export class EvaluateError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public detail?: string
  ) {
    super(message)
    this.name = 'EvaluateError'
  }
}

/**
 * POST /api/evaluate with { prompt, essay }.
 * Always returns unified response with evidence (detailed strengths/weaknesses).
 * Throws EvaluateError on non-2xx, network, or JSON parse errors.
 */
export async function evaluateEssay(payload: EvaluatePayload): Promise<EvaluateResponse> {
  const base = API_BASE ? `${API_BASE.replace(/\/$/, '')}/api/evaluate` : '/api/evaluate'
  let res: Response

  try {
    res = await fetch(base, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: payload.prompt.trim(),
        essay: payload.essay.trim(),
        ...(payload.prompt_id ? { prompt_id: payload.prompt_id } : {}),
      }),
    })
  } catch (err) {
    const raw = err instanceof Error ? err.message : 'Network error'
    const isConnectionError =
      raw === 'Failed to fetch' || /fetch|network|ECONNREFUSED/i.test(raw)
    const message = isConnectionError
      ? 'Backend unreachable. Start it with: uvicorn backend.main:app --reload --port 8000'
      : raw
    throw new EvaluateError(message)
  }

  const text = await res.text()

  if (!res.ok) {
    let detailMessage = text || `Request failed: ${res.status}`
    try {
      const json = JSON.parse(text) as { detail?: string | Array<{ msg?: string }> }
      if (typeof json.detail === 'string') detailMessage = json.detail
      else if (Array.isArray(json.detail) && json.detail.length > 0)
        detailMessage = json.detail.map((d) => d.msg ?? '').filter(Boolean).join('; ') || detailMessage
    } catch { /* use text */ }
    throw new EvaluateError(detailMessage, res.status, detailMessage)
  }

  try {
    const data = JSON.parse(text) as EvaluateResponse
    return data
  } catch {
    throw new EvaluateError('Invalid response from server')
  }
}
