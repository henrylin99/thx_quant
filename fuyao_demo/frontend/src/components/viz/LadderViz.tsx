// 连板天梯矩阵：日期 × 档位（2板..7板+），单元格里是当日该档个股。
// 教学要点：boards 是「档位键 → 个股列表」的嵌套 dict，档位键是英文枚举。
import { msToYmd } from '../../api/client'

const BOARD_LABELS: Record<string, string> = {
  two_board: '2板',
  three_board: '3板',
  four_board: '4板',
  five_board: '5板',
  six_board: '6板',
  seven_over: '7板+',
}

interface LadderRow {
  date_ms?: number
  date?: string
  boards?: Record<string, { name?: string; ticker?: string; board_num?: number; seal_nextday?: number | boolean }[]>
  [k: string]: unknown
}

export default function LadderViz({ data }: { data: unknown }) {
  const rows = (Array.isArray(data) ? data : ((data as { item?: LadderRow[] })?.item ?? [])) as LadderRow[]
  if (!rows.length) {
    return <div className="empty-hint">没有天梯数据；结构不符时请切到「原始 JSON」查看</div>
  }

  const boardKeys = Object.keys(BOARD_LABELS)

  return (
    <div className="table-scroll">
      <table className="data-table ladder-table">
        <thead>
          <tr>
            <th>日期</th>
            {boardKeys.map((k) => <th key={k}>{BOARD_LABELS[k]}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 30).map((row, i) => (
            <tr key={i}>
              <td className="nowrap">{row.date_ms ? msToYmd(row.date_ms) : (row.date ?? '—')}</td>
              {boardKeys.map((k) => {
                const stocks = row.boards?.[k] ?? []
                return (
                  <td key={k} className={stocks.length ? 'ladder-cell' : 'dim'}>
                    {stocks.map((s, j) => (
                      <span key={j} className="ladder-stock" title={`${s.ticker ?? ''} seal_nextday=${s.seal_nextday ?? '—'}`}>
                        {s.name ?? s.ticker}
                      </span>
                    ))}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
