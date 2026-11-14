# fuyao_demo — 扶摇（同花顺金融数据 API）数据查询终端

每个接口一个查询页面：填参数 → 查询 → 表格 / 图表 / JSON。界面风格（深色 Quant Terminal 主题）对齐 `quantitative_analysis` 项目。核心机制是**注册表驱动**：新增一个接口查询页 = 注册表加一条记录，前后端零代码改动。

## 快速开始

```bash
# 1. 后端（Python 3.10+）
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # 填入 FUYAO_API_KEY（https://fuyao.aicubes.cn 申请）
.venv/bin/python app.py     # http://127.0.0.1:5010

# 2. 前端（Node 18+，开发态）
cd ../frontend
npm install
npm run dev                 # http://127.0.0.1:5173（/api 代理到 5010）

# 或：前端构建后由 Flask 同源托管
npm run build               # 然后直接访问 http://127.0.0.1:5010
```

## 架构

```
backend/
├─ app.py               # Flask 入口：/api 蓝图 + 构建产物托管（SPA fallback）
├─ fuyao_client.py      # 扶摇 REST 客户端（认证/信封/节流/时区坑全在此层）
├─ fuyao_registry.py    # ★ 接口注册表：41 个接口页的单一事实来源
└─ api/playground.py    # 通用代理：/api/meta 下发注册表；/api/playground/<id> 白名单调用

frontend/src/
├─ api/client.ts        # 统一请求封装 + 类型 + 北京时间 ms→日期
├─ pages/HomePage.tsx       # 接口目录（按分组）
├─ pages/EndpointPage.tsx   # ★ 通用查询页，完全由注册表驱动
└─ components/
   ├─ JsonTree.tsx          # 原始 JSON 折叠树
   ├─ DataTable.tsx         # 自动推断表格（找 item[] 对象数组）
   └─ viz/                  # 定制图表：K线 / 热榜条形 / 连板天梯矩阵 / 基金收益卡
```

### 每个接口查询页的结构

1. **页头**：接口名 + 路径 chip + 一句话说明
2. **查询条件**：从注册表 params schema 自动生成的参数表单（date_ms 类型给日期选择器）+ 查询按钮；接口的使用约束以小提示列出
3. **查询结果**：耗时 + 三个页签——表格（自动推断）/ 图表（定制 viz）/ JSON（原始折叠树）；业务错误以红色提示条展示 code + message

## 扶摇契约要点（沉淀自 quantitative_analysis 项目实测）

| 要点 | 说明 |
|---|---|
| 认证 | 请求头 `X-api-key`，key 从 `FUYAO_API_KEY` 环境变量读取 |
| 响应信封 | `{code, message, data}`，`code != 0` 即业务错误 |
| 时间口径 | 所有 `*ms` 字段为**北京时间零点** epoch ms，按 UTC 解析会偏一天 |
| 字段双命名 | 快照实测返回 `high_price/prev_price`，文档写 `highest_price/prev_close_price` |
| 批量上限 | 快照/估值 ≤100 只、异动原因 ≤50 只、财务 ≤20 期——各接口不一致 |
| 节流 | 单请求间隔 0.12s（实测 200+ 连发未触发 4001 限频） |
| 文档 vs 实测 | 竞价 stage 文档写 `finallive`，实测合法值为 `live/final` |

## 新增一个接口查询页

1. `backend/fuyao_registry.py` 的 `ENDPOINTS` 加一条记录（id/group/name/path/client_method/doc/tips/params/viz）
2. `backend/fuyao_client.py` 加对应 client 方法
3. 完成。前端页面、导航、表单、表格全部自动生成；如需定制图表，在 `frontend/src/components/viz/` 加组件并在 `VizRouter.tsx` 注册
