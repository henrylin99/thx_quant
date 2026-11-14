// 扶摇接口元数据类型 + 统一请求封装。
// meta 由后端 /api/meta 下发（注册表驱动），前端不硬编码任何接口知识。

export interface ParamDef {
  name: string
  label: string
  type: 'str' | 'int' | 'float' | 'select' | 'codes' | 'date_ms' | 'date_str' | 'bool'
  required?: boolean
  default?: string | number
  options?: string[]
  desc?: string
  placeholder?: string
}

export interface EndpointMeta {
  id: string
  group: string
  name: string
  path: string
  client_method: string
  difficulty: number
  doc: string
  tips: string[]
  params: ParamDef[]
  example_params?: Record<string, string | number>
  viz: string
}

export interface MetaResponse {
  groups: string[]
  error_codes: Record<string, string>
  endpoints: EndpointMeta[]
}

export type CallResult =
  | { ok: true; elapsed_ms: number; data: unknown }
  | { ok: false; code: string; message: string }

export async function fetchMeta(): Promise<MetaResponse> {
  const resp = await fetch('/api/meta')
  if (!resp.ok) throw new Error(`/api/meta HTTP ${resp.status}`)
  return resp.json()
}

export async function callEndpoint(
  id: string,
  params: Record<string, string>,
): Promise<CallResult> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== '' && v != null) qs.set(k, v)
  }
  const resp = await fetch(`/api/playground/${id}?${qs.toString()}`)
  return resp.json()
}

// 扶摇的 *ms 字段均为北京时间零点 epoch ms，按 UTC 解析会偏一天，
// 统一加 8 小时时区偏移后再取日期字符串（教学要点，见各接口贴士）。
export function msToYmd(ms: number): string {
  const d = new Date(ms + 8 * 3600 * 1000)
  return d.toISOString().slice(0, 10)
}
