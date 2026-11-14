// 通用数据表格：从任意扶摇响应里自动推断出「可表格化」的部分。
// 策略（教学要点）：扶摇多数接口返回 {item: [...]} 或纯数组，
// 找到第一个「对象数组」就渲染成表；找不到则退化为键值对表。
import { useMemo } from 'react'

function findRows(data: unknown, depth = 0): Record<string, unknown>[] | null {
  if (depth > 3 || data == null) return null
  if (Array.isArray(data)) {
    const objs = data.filter((x) => x && typeof x === 'object' && !Array.isArray(x))
    if (objs.length > 0 && objs.length === data.length) return objs as Record<string, unknown>[]
    return null
  }
  if (typeof data === 'object') {
    for (const key of ['item', 'items', 'rows', 'list']) {
      const found = findRows((data as Record<string, unknown>)[key], depth + 1)
      if (found) return found
    }
  }
  return null
}

function fmtCell(v: unknown): string {
  if (v == null) return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

export default function DataTable({ data, maxRows = 100 }: { data: unknown; maxRows?: number }) {
  const { rows, columns, kv } = useMemo(() => {
    const rows = findRows(data)
    if (rows) {
      const keys = new Set<string>()
      rows.slice(0, 50).forEach((r) => Object.keys(r).forEach((k) => keys.add(k)))
      return { rows, columns: [...keys], kv: null as [string, unknown][] | null }
    }
    if (data && typeof data === 'object' && !Array.isArray(data)) {
      return { rows: [], columns: [], kv: Object.entries(data as Record<string, unknown>) }
    }
    return { rows: [], columns: [], kv: null }
  }, [data])

  if (kv) {
    return (
      <table className="data-table">
        <thead>
          <tr><th>字段</th><th>值</th></tr>
        </thead>
        <tbody>
          {kv.map(([k, v]) => (
            <tr key={k}><td className="mono">{k}</td><td>{fmtCell(v)}</td></tr>
          ))}
        </tbody>
      </table>
    )
  }

  if (rows.length === 0) {
    return <div className="empty-hint">响应中没有找到对象数组（item[]），请切到「原始 JSON」页签看结构。</div>
  }

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>#</th>
            {columns.map((c) => <th key={c} className="mono">{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, maxRows).map((r, i) => (
            <tr key={i}>
              <td className="dim">{i + 1}</td>
              {columns.map((c) => <td key={c}>{fmtCell(r[c])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > maxRows && <div className="dim pad">共 {rows.length} 行，仅展示前 {maxRows} 行</div>}
    </div>
  )
}
