# 架构设计

fuyao_demo 的核心是一个**注册表驱动（registry-driven）**架构：接口的一切元数据（分组、参数 schema、贴士、可视化类型）都集中在一个 Python 数据结构里，前后端围绕它自动生成页面与路由。

## 代码地图

```text
backend/                      ~1400 行
├─ app.py                     Flask 入口（50 行）：蓝图注册 + 构建产物托管（SPA fallback）
├─ fuyao_client.py            扶摇 REST 客户端（535 行）：认证/信封/节流/时区，全部契约坑在这一层消化
├─ fuyao_registry.py          ★ 接口注册表（715 行）：41 个接口的单一事实来源
└─ api/playground.py          通用代理（100 行）：/api/meta 下发注册表；/api/playground/<id> 白名单调用

frontend/src/                 ~760 行
├─ api/client.ts              统一请求封装 + 类型 + 北京时间 ms→日期
├─ App.tsx                    路由：/ 首页目录、/ep/:id 通用查询页
├─ pages/HomePage.tsx         接口目录（按分组）
├─ pages/EndpointPage.tsx     ★ 通用查询页，完全由注册表驱动
└─ components/
   ├─ JsonTree.tsx            原始 JSON 折叠树
   ├─ DataTable.tsx           自动推断表格（找 item[] 对象数组）
   └─ viz/                    定制图表（见下文）
```

## 注册表：单一事实来源

`fuyao_registry.py` 的 `ENDPOINTS` 列表中，每个接口一条记录：

```python
{
    "id": "snapshot-page",           # URL 标识（/ep/snapshot-page）
    "group": "行情快照",               # 首页分组
    "name": "A 股全市场实时快照（分页）",
    "path": "/api/a-share/prices/snapshot",   # 扶摇原始路径
    "client_method": "snapshot_page",         # fuyao_client 中对应方法
    "difficulty": 1,                 # 教学难度分级
    "doc": "……",                    # 一句话接口说明
    "tips": ["…坑…"],               # 「接口贴士」——实测经验
    "params": [                      # 参数 schema → 前端自动生成表单
        {"name": "limit", "label": "单页条数", "type": "int",
         "required": False, "default": 6000, "desc": "…"},
    ],
    "example_params": {"limit": 20}, # 一键填充示例
    "viz": "table",                  # 可视化类型
}
```

`params.type` 词表：`str / int / float / select / codes / date_ms / date_str / bool`。
`viz` 词表：`candlestick / rank-bar / ladder / returns-cards / table`（默认）。

## 一次查询的完整链路

1. **启动**：前端 `GET /api/meta` 拉取注册表（含分组、参数 schema、错误码表），此后导航、表单、表格全部离线渲染
2. **进入接口页**：`/ep/<id>` → `EndpointPage` 按注册表渲染页头 / 参数表单（`date_ms` 类型给日期选择器）/ 接口贴士
3. **查询**：`GET /api/playground/<id>?参数` → `playground.py` 逐参数校验：
    - **参数白名单**：只放行注册表里声明的参数，杜绝任意参数透传到上游
    - **类型转换**集中在此：`date_ms` 在后端统一转北京时间零点 epoch ms（前端只传 `YYYY-MM-DD`）
4. **调用上游**：`fuyao_client` 加 `X-api-key` 头、执行 0.12s 节流、解析 `{code, message, data}` 信封
5. **响应**：成功 → `{ok: true, elapsed_ms, data}`；业务错误 → `{ok: false, code, message}`（HTTP 仍 200，错误信封本身就是教学素材），前端渲染红色提示卡片
6. **展示**：三个页签——表格（`DataTable` 自动找 `item[]` 对象数组）/ 图表（`VizRouter` 按注册表 `viz` 字段分发）/ JSON（`JsonTree` 折叠树）

## 设计取舍

| 决策 | 理由 |
|------|------|
| 注册表放后端而非前端 | 参数白名单必须由服务端执行，前端 schema 只是体验层；单一来源避免双端漂移 |
| 业务错误返回 HTTP 200 | 扶摇的 `{code, message}` 信封是教学素材，原样透出便于前端渲染错误卡片 |
| 通用查询页而非每接口一页 | 41 个接口共享一个 `EndpointPage`，新增接口 = 加一条注册表记录 |
| 定制图表用 VizRouter 分发 | 90% 接口用默认 table；少数接口（K 线/热榜/天梯/基金收益）按 `viz` 字段挂定制组件，不侵入通用页 |
| 契约坑全部收敛在 client 层 | 时区、双命名、批量上限在 `fuyao_client` 统一处理，上层无需感知 |

## 可视化组件

| 组件 | viz 值 | 用途 |
|------|--------|------|
| `CandlestickViz` | `candlestick` | 历史K线（ECharts） |
| `RankBarViz` | `rank-bar` | 热榜/飙升条形图 |
| `LadderViz` | `ladder` | 连板天梯矩阵 |
| `ReturnsCardsViz` | `returns-cards` | 基金收益卡片 |
| `DataTable`（默认） | `table` | 自动推断表格 |
