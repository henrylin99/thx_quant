// 热榜可视化：排名横向条形图（热股榜 / 飙升榜）。
import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

interface Row {
  name?: string
  rank?: number
  heat?: string | number
  rank_change?: number
  [k: string]: unknown
}

export default function RankBarViz({ data }: { data: unknown }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const rows = (Array.isArray(data) ? data : ((data as { item?: Row[] })?.item ?? [])) as Row[]
    if (!rows.length) return
    const sorted = [...rows].sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999)).slice(0, 30).reverse()

    const chart = echarts.init(ref.current)
    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (ps: { name: string; dataIndex: number }[]) => {
          const r = sorted[ps[0].dataIndex]
          const trend = r.rank_change != null ? `，排名变化 ${r.rank_change > 0 ? '+' : ''}${r.rank_change}` : ''
          return `${r.name}${trend}<br/>热度: ${r.heat ?? '—'}`
        },
      },
      grid: { left: 100, right: 60, top: 10, bottom: 30 },
      xAxis: { type: 'value', name: '热度' },
      yAxis: { type: 'category', data: sorted.map((r) => `${r.rank}. ${r.name}`) },
      series: [
        {
          type: 'bar',
          data: sorted.map((r) => Number(r.heat) || 0),
          itemStyle: { color: '#e11d48' },
          label: { show: true, position: 'right', formatter: (p: { value: number }) => (p.value ? String(p.value) : '') },
        },
      ],
    })
    const onResize = () => chart.resize()
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      chart.dispose()
    }
  }, [data])

  const rows = (Array.isArray(data) ? data : ((data as { item?: Row[] })?.item ?? [])) as Row[]
  if (!rows.length) return <div className="empty-hint">没有可用于绘图的榜单数据</div>
  return <div ref={ref} style={{ width: '100%', height: Math.max(360, rows.length * 26) }} />
}
