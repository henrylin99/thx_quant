// 可视化路由：按注册表的 viz 字段选择定制组件；默认无定制时返回 null（只出表格）。
import CandlestickViz from './viz/CandlestickViz'
import RankBarViz from './viz/RankBarViz'
import LadderViz from './viz/LadderViz'
import ReturnsCardsViz from './viz/ReturnsCardsViz'

export function hasCustomViz(viz: string): boolean {
  return viz !== 'table'
}

export function Viz({ viz, data }: { viz: string; data: unknown }) {
  switch (viz) {
    case 'candlestick':
      return <CandlestickViz data={data} />
    case 'rank-bar':
      return <RankBarViz data={data} />
    case 'ladder':
      return <LadderViz data={data} />
    case 'returns-cards':
      return <ReturnsCardsViz data={data} />
    default:
      return null
  }
}
