// K 线可视化：历史K线 / ETF 历史日线共用。
// 教学要点：date_ms 需按北京时间解析（msToYmd），字段为 open_price/close_price/high_price/low_price。
import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import { msToYmd } from '../../api/client'

interface Bar {
  date_ms: number
  open_price?: number
  close_price?: number
  high_price?: number
  low_price?: number
  volume?: number
  [k: string]: unknown
}

export default function CandlestickViz({ data }: { data: unknown }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const bars = (Array.isArray(data) ? data : ((data as { item?: Bar[] })?.item ?? [])) as Bar[]
    if (!bars.length) return

    const dates = bars.map((b) => msToYmd(b.date_ms))
    const kdata = bars.map((b) => [b.open_price, b.close_price, b.low_price, b.high_price])
    const volumes = bars.map((b) => b.volume ?? 0)

    const chart = echarts.init(ref.current)
    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      grid: [{ left: 60, right: 20, top: 20, height: '55%' }, { left: 60, right: 20, top: '72%', height: '20%' }],
      xAxis: [
        { type: 'category', data: dates, gridIndex: 0, boundaryGap: true },
        { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false } },
      ],
      yAxis: [
        { scale: true, gridIndex: 0 },
        { gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false } },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: kdata,
          xAxisIndex: 0,
          yAxisIndex: 0,
          itemStyle: { color: '#ef4444', color0: '#22c55e', borderColor: '#ef4444', borderColor0: '#22c55e' },
        },
        {
          name: '成交量',
          type: 'bar',
          data: volumes,
          xAxisIndex: 1,
          yAxisIndex: 1,
          itemStyle: { color: '#94a3b8' },
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

  const bars = (Array.isArray(data) ? data : ((data as { item?: Bar[] })?.item ?? [])) as Bar[]
  if (!bars.length) return <div className="empty-hint">没有可用于绘图的 K 线数据</div>
  return <div ref={ref} style={{ width: '100%', height: 420 }} />
}
