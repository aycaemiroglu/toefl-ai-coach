import { useState } from 'react'
import type { EvaluateResponse } from '../lib/api'

interface Props {
  result: EvaluateResponse
}

export default function DebugPanel({ result }: Props) {
  const [open, setOpen] = useState(false)
  const sig = result.confidence.signals

  return (
    <div style={s.wrapper}>
      <button onClick={() => setOpen(!open)} style={s.toggle} type="button">
        <span style={s.icon}>{open ? '\u25BC' : '\u25B6'}</span>
        Debug Signals
      </button>
      {open && (
        <div style={s.content}>
          <table style={s.table}>
            <tbody>
              <Row label="Word count" value={sig.word_count} />
              <Row label="Sentence count" value={result.text_stats.sentence_count} />
              <Row label="Subscore variance" value={sig.subscore_variance.toFixed(1)} />
              <Row label="Weakness count" value={sig.weakness_count} />
              <Row label="Has counterargument weakness" value={sig.has_counterargument_weakness ? 'Yes' : 'No'} />
              <Row label="Raw score" value={result.scoring.raw.toFixed(1)} />
              <Row label="Calibrated score" value={result.scoring.final.toFixed(1)} />
              <Row label="Length penalty" value={result.scoring.length_penalty.toFixed(4)} />
              <Row label="Confidence (before clamp)" value={sig.confidence_before_clamp.toFixed(1)} />
              <Row label="Confidence (after clamp)" value={sig.confidence_after_clamp} />
              <Row label="Length tier" value={result.length.tier} />
              <Row label="Model" value={result.model_name} />
              <Row label="Prompt version" value={result.llm_config.prompt_version} />
              <Row label="Temperature" value={result.llm_config.temperature} />
              <Row label="Max tokens" value={result.llm_config.max_tokens} />
              <Row label="Latency" value={`${result.timestamps.latency_ms} ms`} />
              <Row label="Request ID" value={result.request_id} mono />
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Row({ label, value, mono }: { label: string; value: string | number; mono?: boolean }) {
  return (
    <tr>
      <td style={s.tdLabel}>{label}</td>
      <td style={{ ...s.tdValue, ...(mono ? s.mono : {}) }}>{value}</td>
    </tr>
  )
}

const s: Record<string, React.CSSProperties> = {
  wrapper: {
    borderRadius: 10,
    border: '1px dashed #cbd5e1',
    overflow: 'hidden',
  },
  toggle: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    width: '100%',
    padding: '10px 14px',
    border: 'none',
    background: '#f8fafc',
    cursor: 'pointer',
    fontSize: '0.78rem',
    fontWeight: 600,
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  icon: { fontSize: '0.6rem' },
  content: { padding: '4px 14px 14px' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' },
  tdLabel: { padding: '4px 8px 4px 0', color: '#64748b', whiteSpace: 'nowrap' },
  tdValue: { padding: '4px 0', color: '#0f172a', fontWeight: 500, textAlign: 'right' },
  mono: { fontFamily: 'ui-monospace, monospace', fontSize: '0.75rem', color: '#64748b' },
}
