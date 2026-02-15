/**
 * API client for TOEFL essay evaluation.
 * Backend: POST /api/evaluate (proxied to localhost:8000 in dev).
 */

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export interface EvaluatePayload {
  prompt: string
  essay: string
}

export interface Subscores {
  task_response: number
  coherence_cohesion: number
  lexical_resource: number
  grammar: number
}

export interface Confidence {
  level: 'Low' | 'Medium' | 'High'
  reason: string
}

/** Detailed strength/weakness item (when using ?detailed=true). Weaknesses may include evidence_reason when evidence is null. */
export interface StrengthWeaknessItem {
  label: string
  explanation: string
  evidence: string | null
  evidence_reason?: string | null
}

export interface EvaluateResponse {
  model: string
  estimated_score: number
  subscores: Subscores
  confidence?: Confidence
  /** Legacy: string[]. With ?detailed=true: StrengthWeaknessItem[] */
  strengths: string[] | StrengthWeaknessItem[]
  weaknesses: string[] | StrengthWeaknessItem[]
  top_fixes: string[]
  rewrite_first_paragraph: string
  word_count: number
  latency_ms: number
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
 * Uses ?detailed=true to get strengths/weaknesses as { label, explanation, evidence }.
 * Throws EvaluateError on non-2xx, network, or JSON parse errors.
 */
export async function evaluateEssay(payload: EvaluatePayload): Promise<EvaluateResponse> {
  const base = API_BASE ? `${API_BASE.replace(/\/$/, '')}/api/evaluate` : '/api/evaluate'
  const url = `${base}?detailed=true`
  let res: Response

  try {
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: payload.prompt.trim(),
        essay: payload.essay.trim(),
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
