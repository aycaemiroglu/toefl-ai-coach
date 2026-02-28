import type { Evidence } from '../lib/api'

interface Props {
  evidence: Evidence
}

export default function EvidenceSection({ evidence }: Props) {
  return (
    <div style={s.wrapper}>
      {/* Strengths */}
      <div style={s.section}>
        <h3 style={s.sectionTitle}>
          <span style={s.strengthDot} />
          Strengths
          <span style={s.count}>{evidence.strengths.length}</span>
        </h3>
        {evidence.strengths.map((item, i) => (
          <div key={i} style={s.item}>
            <div style={s.itemLabel}>{item.label}</div>
            <div style={s.itemExplanation}>{item.explanation}</div>
            {item.evidence != null && item.evidence !== '' ? (
              <blockquote style={s.quote}>
                <span style={s.quoteIcon}>&ldquo;</span>
                {item.evidence}
              </blockquote>
            ) : item.evidence_fallback ? (
              <div style={s.fallback}>{item.evidence_fallback}</div>
            ) : null}
          </div>
        ))}
      </div>

      {/* Weaknesses */}
      <div style={s.section}>
        <h3 style={s.sectionTitle}>
          <span style={s.weaknessDot} />
          Weaknesses
          <span style={s.count}>{evidence.weaknesses.length}</span>
        </h3>
        {evidence.weaknesses.map((item, i) => (
          <div key={i} style={s.item}>
            <div style={s.itemLabel}>{item.label}</div>
            <div style={s.itemExplanation}>{item.explanation}</div>
            {item.evidence != null && item.evidence !== '' ? (
              <blockquote style={{ ...s.quote, borderLeftColor: '#f59e0b' }}>
                <span style={{ ...s.quoteIcon, color: '#d97706' }}>&ldquo;</span>
                {item.evidence}
              </blockquote>
            ) : (
              <div style={s.fallback}>
                {item.evidence_fallback ?? 'No direct quote available.'}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  wrapper: {
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
  },
  section: {},
  sectionTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    margin: '0 0 12px',
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  strengthDot: {
    display: 'inline-block',
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#10b981',
  },
  weaknessDot: {
    display: 'inline-block',
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#f59e0b',
  },
  count: {
    marginLeft: 2,
    padding: '1px 7px',
    borderRadius: 10,
    fontSize: '0.7rem',
    fontWeight: 700,
    background: '#f1f5f9',
    color: '#64748b',
  },
  item: {
    padding: '12px 14px',
    background: '#fff',
    borderRadius: 10,
    border: '1px solid #e2e8f0',
    marginBottom: 8,
  },
  itemLabel: { fontSize: '0.9rem', fontWeight: 600, color: '#0f172a', marginBottom: 2 },
  itemExplanation: { fontSize: '0.85rem', color: '#475569', lineHeight: 1.5 },
  quote: {
    margin: '8px 0 0',
    padding: '8px 12px',
    borderLeft: '3px solid #10b981',
    background: '#f8fafc',
    borderRadius: '0 6px 6px 0',
    fontSize: '0.84rem',
    color: '#334155',
    fontStyle: 'italic',
    lineHeight: 1.5,
    position: 'relative',
  },
  quoteIcon: {
    fontSize: '1.2rem',
    color: '#10b981',
    marginRight: 4,
    fontStyle: 'normal',
    lineHeight: 1,
  },
  fallback: {
    marginTop: 6,
    fontSize: '0.8rem',
    color: '#94a3b8',
    fontStyle: 'italic',
  },
}
