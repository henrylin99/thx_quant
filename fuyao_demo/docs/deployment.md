# 部署运维

## 两种运行形态

### 形态 A：开发态（前后端分离）

```bash
# 终端 1 —— 后端
cd backend
.venv/bin/python app.py            # http://127.0.0.1:5010

# 终端 2 —— 前端 Vite dev server
cd frontend
npm run dev                        # http://127.0.0.1:5173，/api 代理到 5010
```

访问 **5173**。热更新、接口代理由 Vite `server.proxy` 配置。

### 形态 B：构建产物同源托管（单进程）

```bash
cd frontend && npm run build       # 产物 → frontend/dist
cd ../backend && .venv/bin/python app.py
```

直接访问 **5010**：Flask 托管 `dist/` 静态资源，非资源路径（如 `/ep/limit-up-pool`）经 SPA fallback 回退到 `index.html` 交给前端路由。**部署只需一个 Python 进程**。

## 环境变量

| 变量 | 位置 | 说明 |
|---|---|---|
| `FUYAO_API_KEY` | `backend/.env` | 扶摇 API key（python-dotenv 加载），缺失时所有查询返回 `no_key` |

`.env` 已被 `.gitignore` 排除，`backend/.env.example` 是模板。

## 安全清单

本项目定位教学，默认宽松；对外开放前至少收紧：

- [ ] `app.py` 的 `CORS(app)` 是全放开——生产应收紧 `origins`
- [ ] `FUYAO_API_KEY` 只存在后端，前端永远拿不到（playground 是白名单代理，不是透传代理）
- [ ] 若公网部署，`app.py` 的 Flask dev server 换 gunicorn/waitress（`app:app`）
- [ ] 评估是否给 `/api/playground/*` 加自己的限流（当前只依赖 client 层 0.12s 节流）

```bash
# 生产示例
.venv/bin/pip install gunicorn
.venv/bin/gunicorn -w 2 -b 0.0.0.0:5010 app:app
```

## 文档站点

本项目的 MkDocs 站点由 thx_quant 仓库的 GitHub Actions 自动构建部署：

- 源：`fuyao_demo/docs/`（接口目录由 `scripts/gen_endpoint_catalog.py` 从注册表自动生成，**不要手改** `endpoints.md`）
- 触发：push 到 main 且改动 `fuyao_demo/**`
- 地址：https://fuyao.chcc.blog/
