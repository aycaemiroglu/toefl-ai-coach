import { useState } from 'react'
import type { Confidence } from '../lib/api'

const levelStyle: Record<string, { bg: string; text: string; barColor: string }> = {
  High: { bg: '#d1fae5', text: '#065f46', barColor: '#10b981' },
  Medium: { bg: '#fef3c7', text: '#92400e', barColor: '#f59e0b' },
  Low: { bg: '#fee2e2', text: '#991b1b', barColor: '#ef4444' },
}

interface Props {
  confidence: Confidence
}

export default function ConfidenceCard({ confidence }: Props) {
  const [expanded, setExpanded] = useState(false)
  const ls = levelStyle[confidence.level] ?? levelStyle.Medium

  return (
    <div style={s.card}>
      <div style={s.header}>
        <span style={s.label}>Confidence</span>
        <span style={{ ...s.badge, background: ls.bg, color: ls.text }}>
          {confidence.level}
        </span>
      </div>

      <div style={s.scoreRow}>
        <span style={s.numericScore}>{confidence.score}</span>
        <span style={s.outOf}>/ 100</span>
      </div>

      <div style={s.barOuter}>
        <div style={{ ...s.barInner, width: `${confidence.score}%`, background: ls.barColor }} />
      </div>

      {confidence.reasons.length > 0 && (
        <div style={s.reasonsContainer}>
          <button
            onClick={() => setExpanded(!expanded)}
            style={s.reasonsToggle}
            type="button"
          >
            <span style={s.arrow}>{expanded ? '\u25BC' : '\u25B6'}</span>
            Why {confidence.level}?
          </button>
          {expanded && (
            <ul style={s.reasonsList}>
              {confidence.reasons.map((r, i) => (
                <li key={i} style={s.reasonItem}>{r}</li>
              ))}
            </ul>
          )}
        </div>
      )}
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
  badge: {
    display: 'inline-block',
    padding: '3px 12px',
    borderRadius: 20,
    fontSize: '0.8rem',
    fontWeight: 700,
  },
  scoreRow: { display: 'flex', alignItems: 'baseline', gap: 4 },
  numericScore: { fontSize: '2rem', fontWeight: 800, color: '#0f172a', lineHeight: 1 },
  outOf: { fontSize: '1rem', color: '#94a3b8', fontWeight: 500 },
  barOuter: {
    marginTop: 10,
    height: 6,
    background: '#e2e8f0',
    borderRadius: 3,
    overflow: 'hidden',
  },
  barInner: {
    height: '100%',
    borderRadius: 3,
    transition: 'width 0.4s ease',
  },
  reasonsContainer: {
    marginTop: 12,
    background: '#f8fafc',
    borderRadius: 8,
    overflow: 'hidden',
  },
  reasonsToggle: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    width: '100%',
    padding: '8px 12px',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    fontSize: '0.82rem',
    fontWeight: 600,
    color: '#475569',
    textAlign: 'left',
  },
  arrow: { fontSize: '0.65rem' },
  reasonsList: {
    margin: 0,
    padding: '0 12px 10px 28px',
    listStyle: 'disc',
  },
  reasonItem: {
    fontSize: '0.82rem',
    color: '#64748b',
    marginBottom: 3,
    lineHeight: 1.4,
  },
}
