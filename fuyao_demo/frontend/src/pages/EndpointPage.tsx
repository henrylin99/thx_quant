// 通用接口查询页：页头 → 查询表单 → 结果（表格/可视化/JSON）。由后端 /api/meta 注册表驱动。
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { callEndpoint, type CallResult, type EndpointMeta, type MetaResponse, type ParamDef } from '../api/client'
import JsonTree from '../components/JsonTree'
import DataTable from '../components/DataTable'
import { Viz, hasCustomViz } from '../components/VizRouter'

type FormState = Record<string, string>

function initialValues(ep: EndpointMeta): FormState {
  const state: FormState = {}
  for (const p of ep.params) {
    const ex = ep.example_params?.[p.name]
    if (ex != null) state[p.name] = String(ex)
    else if (p.default != null) state[p.name] = String(p.default)
    else state[p.name] = ''
  }
  return state
}

function ParamInput({ p, value, onChange }: { p: ParamDef; value: string; onChange: (v: string) => void }) {
  if (p.type === 'select') {
    return (
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {p.options?.map((o) => <option key={o} value={o}>{o === '' ? '（默认）' : o}</option>)}
      </select>
    )
  }
  if (p.type === 'bool') {
    return (
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">（默认）</option>
        <option value="true">true</option>
        <option value="false">false</option>
      </select>
    )
  }
  if (p.type === 'date_ms' || p.type === 'date_str') {
    return <input type="date" value={value} onChange={(e) => onChange(e.target.value)} />
  }
  return (
    <input
      type="text"
      value={value}
      placeholder={p.placeholder ?? (p.type === 'codes' ? '逗号分隔多个' : '')}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

type TabKey = 'table' | 'viz' | 'json'
const TAB_LABELS: Record<TabKey, string> = { table: '表格', viz: '图表', json: 'JSON' }

export default function EndpointPage({ meta }: { meta: MetaResponse | null }) {
  const { endpointId } = useParams<{ endpointId: string }>()
  const ep = useMemo(() => meta?.endpoints.find((e) => e.id === endpointId), [meta, endpointId])
  const [form, setForm] = useState<FormState>({})
  const [result, setResult] = useState<CallResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState<TabKey>('table')

  useEffect(() => {
    if (ep) {
      setForm(initialValues(ep))
      setResult(null)
      setTab(hasCustomViz(ep.viz) ? 'viz' : 'table')
    }
  }, [ep])

  if (!meta) return <div className="pad dim">加载接口清单…</div>
  if (!ep) return <div className="pad">未知接口: {endpointId}</div>

  const set = (name: string, v: string) => setForm((f) => ({ ...f, [name]: v }))

  const run = async () => {
    setLoading(true)
    try {
      const r = await callEndpoint(ep.id, form)
      setResult(r)
      setTab(hasCustomViz(ep.viz) ? 'viz' : 'table')
    } finally {
      setLoading(false)
    }
  }

  const errorCodeMeaning = result && !result.ok ? meta.error_codes[result.code] : undefined

  return (
    <div className="endpoint-page">
      {/* 页头 */}
      <header className="page-head">
        <div>
          <h1>{ep.name}</h1>
          <p className="page-desc">{ep.doc}</p>
        </div>
        <span className="endpoint-path">{ep.path}</span>
      </header>

      {/* 查询条件 */}
      <section className="card">
        <div className="card-head"><h2>查询条件</h2></div>
        {ep.tips.length > 0 && (
          <div className="hint">
            <ul>{ep.tips.map((t, i) => <li key={i}>{t}</li>)}</ul>
          </div>
        )}
        {ep.params.length === 0 ? (
          <div className="dim">本接口无参数。</div>
        ) : (
          <div className="param-grid">
            {ep.params.map((p) => (
              <label key={p.name} className="param-row">
                <span className="param-label">
                  <code>{p.name}</code>
                  {p.required && <em className="required">*</em>}
                  <span className="param-cn">{p.label}</span>
                </span>
                <ParamInput p={p} value={form[p.name] ?? ''} onChange={(v) => set(p.name, v)} />
                {p.desc && <span className="param-desc">{p.desc}</span>}
              </label>
            ))}
          </div>
        )}
        <button className="run-btn" onClick={run} disabled={loading}>
          {loading ? '查询中…' : '查询'}
        </button>
      </section>

      {/* 错误提示 */}
      {result && !result.ok && (
        <section className="card error-card">
          <p style={{ margin: 0 }}>
            <span className="err-code mono">code {result.code}</span>　{result.message}
          </p>
          {errorCodeMeaning && <p className="err-meaning">{errorCodeMeaning}</p>}
        </section>
      )}

      {/* 查询结果 */}
      {loading && (
        <section className="card skeleton-rows">
          {[0, 1, 2, 3, 4].map((i) => <div key={i} className="skeleton-line" style={{ width: `${90 - i * 12}%` }} />)}
        </section>
      )}
      {result && result.ok && (
        <section className="card">
          <div className="card-head">
            <h2>查询结果</h2>
            <div className="result-meta">
              <span>耗时 <span className="mono">{result.elapsed_ms} ms</span></span>
            </div>
            <div className="tabs">
              {(['table', 'viz', 'json'] as TabKey[])
                .filter((t) => t !== 'viz' || hasCustomViz(ep.viz))
                .map((t) => (
                  <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
                    {TAB_LABELS[t]}
                  </button>
                ))}
            </div>
          </div>
          {tab === 'table' && <DataTable data={result.data} />}
          {tab === 'viz' && <Viz viz={ep.viz} data={result.data} />}
          {tab === 'json' && <JsonTree data={result.data} />}
        </section>
      )}
    </div>
  )
}
