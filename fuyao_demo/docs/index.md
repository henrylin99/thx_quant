# fuyao_demo 文档

扶摇（同花顺官方金融数据 API）数据查询终端——41 个接口 × 8 个分组，注册表驱动，新增接口查询页零前后端代码改动。

```text
填参数 → 查询 → 表格 / 图表 / JSON
```

## 文档目录

| 文档 | 内容 |
|------|------|
| [架构设计](architecture.md) | 注册表驱动机制、请求全链路、设计取舍 |
| [扶摇 API 契约手册](api-contract.md) | 认证 / 信封 / 时区坑 / 字段双命名 / 错误码全集 |
| [接口目录](endpoints.md) | 41 个接口的参数、限制与贴士（由注册表自动生成） |
| [扩展指南](extending.md) | 如何新增接口查询页 / 定制图表组件 |
| [部署运维](deployment.md) | 开发态、构建托管、环境变量与安全清单 |

## 快速开始

```bash
# 后端（Python 3.10+）
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # 填入 FUYAO_API_KEY（https://fuyao.aicubes.cn 申请）
.venv/bin/python app.py     # http://127.0.0.1:5010

# 前端（Node 18+，开发态）
cd ../frontend
npm install
npm run dev                 # http://127.0.0.1:5173（/api 代理到 5010）
```

## 一图看懂

```text
┌──────────────┐   GET /api/meta（注册表）    ┌───────────────────┐
│   前端 React  │ ◄────────────────────────── │  Flask 后端        │
│  EndpointPage │                              │  playground 蓝图   │
│  （通用查询页）│  GET /api/playground/<id>   │  （参数白名单）     │
│              │ ──────────────────────────► │        │           │
└──────────────┘   只放行注册表声明的参数       └────────▼──────────┘
                                              fuyao_client.py
                                              （认证/信封/节流/时区）
                                                   │
                                                   ▼
                                          fuyao.aicubes.cn REST
```
