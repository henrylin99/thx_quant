import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { fetchMeta, type MetaResponse } from './api/client'
import HomePage from './pages/HomePage'
import EndpointPage from './pages/EndpointPage'

export default function App() {
  const [meta, setMeta] = useState<MetaResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchMeta()
      .then(setMeta)
      .catch((e) => setError(String(e)))
  }, [])

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-title">扶摇数据终端</div>
          <div className="brand-sub">fuyao · 同花顺金融数据 API</div>
        </div>
        <nav>
          <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            全部接口
          </NavLink>
          {meta?.groups
            .filter((g) => meta.endpoints.some((e) => e.group === g))
            .map((group) => (
              <div key={group} className="nav-group">
                <div className="nav-group-label">{group}</div>
                {meta.endpoints
                  .filter((e) => e.group === group)
                  .map((e) => (
                    <NavLink
                      key={e.id}
                      to={`/ep/${e.id}`}
                      className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                    >
                      {e.name}
                    </NavLink>
                  ))}
              </div>
            ))}
        </nav>
      </aside>
      <main className="main">
        {error && <div className="pad error-card">后端未启动或 /api/meta 不可达：{error}（请先启动 backend/app.py）</div>}
        <Routes>
          <Route path="/" element={<HomePage meta={meta} />} />
          <Route path="/ep/:endpointId" element={<EndpointPage meta={meta} />} />
        </Routes>
      </main>
    </div>
  )
}
