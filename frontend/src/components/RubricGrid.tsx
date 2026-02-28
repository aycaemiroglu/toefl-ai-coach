import type { Rubric } from '../lib/api'

const LABELS: Record<keyof Rubric, string> = {
  task_response: 'Task Response',
  coherence: 'Coherence & Cohesion',
  lexical: 'Lexical Resource',
  grammar: 'Grammar',
}

function scoreColor(v: number): string {
  if (v >= 4.5) return '#059669'
  if (v >= 3.5) return '#0284c7'
  if (v >= 2.5) return '#d97706'
  return '#dc2626'
}

interface Props {
  rubric: Rubric
}

export default function RubricGrid({ rubric }: Props) {
  return (
    <div style={s.wrapper}>
      <h3 style={s.title}>Rubric Breakdown</h3>
      <div style={s.grid}>
        {(Object.keys(LABELS) as Array<keyof Rubric>).map((key) => {
          const v = rubric[key]
          const pct = (v / 5) * 100
          return (
            <div key={key} style={s.card}>
              <div style={s.label}>{LABELS[key]}</div>
              <div style={{ ...s.score, color: scoreColor(v) }}>
                {v.toFixed(1)} <span style={s.dim}>/ 5</span>
              </div>
              <div style={s.barOuter}>
                <div style={{ ...s.barInner, width: `${pct}%`, background: scoreColor(v) }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  wrapper: { marginBottom: 0 },
  title: { margin: '0 0 10px', fontSize: '0.8rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 10,
  },
  card: {
    padding: '12px 14px',
    background: '#fff',
    borderRadius: 10,
    border: '1px solid #e2e8f0',
  },
  label: { fontSize: '0.78rem', color: '#64748b', marginBottom: 4 },
  score: { fontSize: '1.25rem', fontWeight: 700, lineHeight: 1 },
  dim: { fontSize: '0.8rem', fontWeight: 400, color: '#94a3b8' },
  barOuter: {
    marginTop: 8,
    height: 4,
    background: '#e2e8f0',
    borderRadius: 2,
    overflow: 'hidden',
  },
  barInner: {
    height: '100%',
    borderRadius: 2,
    transition: 'width 0.4s ease',
  },
}
