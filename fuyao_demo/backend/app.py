"""fuyao_demo 后端入口。

开发态：python app.py → http://127.0.0.1:5010
前端 Vite dev server（5173）通过代理把 /api 转发过来。
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, send_from_directory
from flask_cors import CORS

from api.playground import bp as playground_bp

app = Flask(__name__, static_folder=None)
CORS(app)  # 教学项目：本地全放开；生产环境应收紧 origins

app.register_blueprint(playground_bp)

# 构建产物托管：npm run build 后直接由 Flask 同源服务（可选）
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@app.route("/")
def index():
    if (_FRONTEND_DIST / "index.html").exists():
        return send_from_directory(_FRONTEND_DIST, "index.html")
    return (
        "fuyao_demo 后端运行中。<br>"
        "前端开发态请访问 http://127.0.0.1:5173；"
        "或先 cd frontend &amp;&amp; npm run build 再访问本页。"
    )


@app.route("/<path:asset>")
def frontend_assets(asset: str):
    # SPA fallback：非静态资源路径（如 /ep/limit-up-pool）回退到 index.html 交给前端路由
    if (_FRONTEND_DIST / asset).exists():
        return send_from_directory(_FRONTEND_DIST, asset)
    if (_FRONTEND_DIST / "index.html").exists():
        return send_from_directory(_FRONTEND_DIST, "index.html")
    return "Not Found", 404


if __name__ == "__main__":
    import os

    print(" * FUYAO_API_KEY:", "已配置" if os.getenv("FUYAO_API_KEY", "").strip() else "未配置（请在 backend/.env 设置）")
    app.run(host="127.0.0.1", port=5010, debug=True)
