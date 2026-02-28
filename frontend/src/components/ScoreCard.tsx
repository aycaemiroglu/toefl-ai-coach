import type { Scoring, LengthEvaluation } from '../lib/api'

const tierColors: Record<string, { bg: string; border: string; text: string }> = {
  short: { bg: '#fef3c7', border: '#f59e0b', text: '#92400e' },
  recommended: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af' },
  ideal: { bg: '#d1fae5', border: '#10b981', text: '#065f46' },
}

interface Props {
  scoring: Scoring
  length: LengthEvaluation
}

export default function ScoreCard({ scoring, length }: Props) {
  const tier = tierColors[length.tier] ?? tierColors.recommended
  const hasCalibration = scoring.length_penalty < 1

  return (
    <div style={s.card}>
      <div style={s.header}>
        <span style={s.label}>Overall Score</span>
        <span style={{ ...s.tierBadge, background: tier.bg, color: tier.text, borderColor: tier.border }}>
          {length.tier}
        </span>
      </div>

      <div style={s.scoreRow}>
        <span style={s.bigScore}>{scoring.final.toFixed(1)}</span>
        <span style={s.outOf}>/ 30</span>
        {hasCalibration && <span style={s.calibratedTag}>Calibrated</span>}
      </div>

      {hasCalibration && (
        <div style={s.breakdown}>
          <span>Raw: <strong>{scoring.raw.toFixed(1)}</strong></span>
          <span style={s.sep}>&times;</span>
          <span>Length factor: <strong>{scoring.length_penalty.toFixed(2)}</strong></span>
          <span style={s.sep}>=</span>
          <span>Final: <strong>{scoring.final.toFixed(1)}</strong></span>
        </div>
      )}

      <div style={s.tierMessage}>{length.message}</div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: {
    padding: 20,
    background: '#fff',
    borderRadius: 12,
    border: '1px solid #e2e8f0',
    boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  label: { fontSize: '0.8rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' },
  tierBadge: {
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 20,
    fontSize: '0.75rem',
    fontWeight: 600,
    border: '1px solid',
    textTransform: 'capitalize',
  },
  scoreRow: { display: 'flex', alignItems: 'baseline', gap: 6 },
  bigScore: { fontSize: '2.8rem', fontWeight: 800, color: '#0f172a', lineHeight: 1 },
  outOf: { fontSize: '1.1rem', color: '#94a3b8', fontWeight: 500 },
  calibratedTag: {
    marginLeft: 10,
    padding: '2px 8px',
    borderRadius: 4,
    fontSize: '0.7rem',
    fontWeight: 600,
    background: '#e0e7ff',
    color: '#4338ca',
  },
  breakdown: {
    marginTop: 10,
    padding: '8px 12px',
    background: '#f8fafc',
    borderRadius: 6,
    fontSize: '0.82rem',
    color: '#475569',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  sep: { color: '#94a3b8' },
  tierMessage: {
    marginTop: 10,
    padding: '6px 10px',
    fontSize: '0.85rem',
    color: '#475569',
    background: '#f1f5f9',
    borderRadius: 6,
    borderLeft: '3px solid #94a3b8',
  },
}
