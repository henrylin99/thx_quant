// 通用 JSON 折叠树：教学项目里「先看原始响应结构」是最重要的一步。
import { useState, type ReactNode } from 'react'

function primitive(value: unknown): ReactNode {
  if (typeof value === 'string') return <span className="json-str">"{value}"</span>
  if (typeof value === 'number') return <span className="json-num">{value}</span>
  if (typeof value === 'boolean') return <span className="json-bool">{String(value)}</span>
  if (value === null || value === undefined) return <span className="json-null">null</span>
  return <span className="json-num">{String(value)}</span>
}

function JsonNode({ name, value, depth }: { name?: string; value: unknown; depth: number }) {
  const [open, setOpen] = useState(depth < 2)

  if (value === null || value === undefined || typeof value !== 'object') {
    return (
      <div className="json-line" style={{ paddingLeft: depth * 16 }}>
        {name !== undefined && <span className="json-key">{name}: </span>}
        {primitive(value)}
      </div>
    )
  }

  const isArr = Array.isArray(value)
  const entries: [string, unknown][] = isArr
    ? (value as unknown[]).map((v, i) => [String(i), v])
    : Object.entries(value as Record<string, unknown>)

  return (
    <div className="json-line" style={{ paddingLeft: depth * 16 }}>
      <span className="json-toggle" onClick={() => setOpen(!open)}>
        {open ? '▼' : '▶'}
      </span>
      {name !== undefined && <span className="json-key">{name}: </span>}
      <span className="json-bracket">{isArr ? '[' : '{'}</span>
      {!open && (
        <>
          <span className="json-dim">…{entries.length} 项</span>
          <span className="json-bracket">{isArr ? ']' : '}'}</span>
        </>
      )}
      {open && (
        <>
          {entries.slice(0, 100).map(([k, v]) => (
            <JsonNode key={k} name={k} value={v} depth={depth + 1} />
          ))}
          {entries.length > 100 && <div className="json-dim" style={{ paddingLeft: (depth + 1) * 16 }}>…共 {entries.length} 项，已截断</div>}
          <div style={{ paddingLeft: depth * 16 }}>
            <span className="json-bracket">{isArr ? ']' : '}'}</span>
          </div>
        </>
      )}
    </div>
  )
}

export default function JsonTree({ data }: { data: unknown }) {
  return (
    <div className="json-tree">
      <JsonNode value={data} depth={0} />
    </div>
  )
}
