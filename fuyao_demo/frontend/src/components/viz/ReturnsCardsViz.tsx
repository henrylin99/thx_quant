// 基金区间收益/回撤卡片视图：return_X vs peer_average_X 配对展示 + 同类排名。
// 教学要点：这类接口返回扁平 dict（或 {item:[dict]}），字段按后缀 _month/_fyear 分组。
const PERIOD_LABELS: Record<string, string> = {
  week: '近一周',
  month: '近一月',
  tmonth: '近三月',
  hyear: '近半年',
  fyear: '近一年',
  nowyear: '今年以来',
  now: '成立以来',
  year: '近一年',
  quarter: '近一季',
  half: '近半年',
}

interface Pair { period: string; self: number | null; peer: number | null; rank?: string }

function extractPairs(data: unknown): { pairs: Pair[]; isDrawdown: boolean } {
  let obj: Record<string, unknown> | null = null
  if (Array.isArray(data)) obj = (data[0] ?? null) as Record<string, unknown> | null
  else if (data && typeof data === 'object') {
    const d = data as Record<string, unknown>
    const item = (Array.isArray(d.item) ? (d.item as unknown[])[0] : null) as Record<string, unknown> | null
    obj = item ?? d
  }
  if (!obj) return { pairs: [], isDrawdown: false }

  const isDrawdown = Object.keys(obj).some((k) => /drawdown|max_/.test(k))
  const periods = new Set<string>()
  for (const k of Object.keys(obj)) {
    const m = k.match(/(?:return|peer_average|max_drawdown)_(\w+)$/)
    if (m) periods.add(m[1])
  }
  const pairs: Pair[] = []
  for (const p of periods) {
    const selfKey = isDrawdown ? `max_drawdown_${p}` : `return_${p}`
    const peerKey = isDrawdown ? null : `peer_average_${p}`
    pairs.push({
      period: p,
      self: (obj[selfKey] as number) ?? null,
      peer: peerKey ? ((obj[peerKey] as number) ?? null) : null,
      rank: (obj[`rank_${p}`] as string) ?? undefined,
    })
  }
  return { pairs, isDrawdown }
}

function fmtPct(v: number | null): string {
  if (v == null || Number.isNaN(v)) return '—'
  return `${v > 0 ? '+' : ''}${v.toFixed(2)}%`
}

export default function ReturnsCardsViz({ data }: { data: unknown }) {
  const { pairs, isDrawdown } = extractPairs(data)
  if (!pairs.length) return <div className="empty-hint">没有可展示的区间指标（结构不符请看原始 JSON）</div>

  return (
    <div className="cards-grid">
      {pairs.map((p) => (
        <div key={p.period} className="stat-card">
          <div className="stat-title">{PERIOD_LABELS[p.period] ?? p.period}</div>
          <div className={`stat-value ${p.self != null && p.self > 0 !== isDrawdown ? 'pos' : 'neg'}`}>
            {isDrawdown ? p.self?.toFixed(2) + '%' : fmtPct(p.self)}
          </div>
          {!isDrawdown && <div className="stat-sub">同类均值 {fmtPct(p.peer)}</div>}
          {p.rank && <div className="stat-sub">同类排名 {p.rank}</div>}
        </div>
      ))}
    </div>
  )
}
