// 首页：接口目录（按分组）。
import { Link } from 'react-router-dom'
import { GROUP_ORDER } from '../data/groupOrder'
import type { MetaResponse } from '../api/client'

export default function HomePage({ meta }: { meta: MetaResponse | null }) {
  if (!meta) return <div className="pad dim">加载接口清单…</div>

  const groups = GROUP_ORDER.filter((g) => meta.endpoints.some((e) => e.group === g))
  const orphans = meta.endpoints.filter((e) => !GROUP_ORDER.includes(e.group))
  for (const e of orphans) if (!groups.includes(e.group)) groups.push(e.group)

  return (
    <div className="home-page">
      <header className="page-head">
        <div>
          <h1>全部接口</h1>
          <p className="page-desc">共 {meta.endpoints.length} 个接口，每个接口一个查询页面：填参数 → 查询 → 表格 / 图表 / JSON。</p>
        </div>
      </header>

      {groups.map((group) => (
        <section key={group} className="card">
          <h2 className="group-title">{group}</h2>
          <div className="endpoint-cards">
            {meta.endpoints.filter((e) => e.group === group).map((e) => (
              <Link key={e.id} to={`/ep/${e.id}`} className="endpoint-card">
                <div className="endpoint-card-head">
                  <span className="endpoint-name">{e.name}</span>
                </div>
                <div className="endpoint-card-path">{e.path}</div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
