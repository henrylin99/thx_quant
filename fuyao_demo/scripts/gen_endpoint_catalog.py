#!/usr/bin/env python3
"""Generate docs/endpoints.md from backend/fuyao_registry.py.

The registry is the single source of truth; this script renders it into a
browsable catalog page. Run before `mkdocs build` in CI. Output is gitignored.
"""
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from fuyao_registry import ENDPOINTS, ERROR_CODES  # noqa: E402

TYPE_LABEL = {
    "str": "文本", "int": "整数", "float": "小数", "select": "下拉",
    "codes": "代码列表", "date_ms": "日期", "date_str": "日期", "bool": "开关",
}
VIZ_LABEL = {
    "table": "表格", "candlestick": "K线", "rank-bar": "条形图",
    "ladder": "天梯矩阵", "returns-cards": "收益卡片",
}


def main() -> int:
    groups = defaultdict(list)
    for ep in ENDPOINTS:
        groups[ep["group"]].append(ep)

    out = [
        "# 接口目录",
        "",
        f"共 **{len(ENDPOINTS)}** 个接口 / {len(groups)} 个分组。"
        "本页由 `scripts/gen_endpoint_catalog.py` 从 `fuyao_registry.py` 自动生成，**请勿手改**。",
        "",
    ]
    for group, eps in groups.items():
        out += [f"## {group}（{len(eps)}）", ""]
        for ep in eps:
            out += [
                f"### {ep['name']}",
                "",
                f"`{ep['path']}` · 难度 {'★' * ep.get('difficulty', 1)} · "
                f"可视化：{VIZ_LABEL.get(ep.get('viz', 'table'), ep.get('viz'))} · "
                f"本地体验：`/ep/{ep['id']}`（启动 fuyao_demo 后访问）",
                "",
                ep.get("doc", "").strip(),
                "",
            ]
            params = ep.get("params", [])
            if params:
                out += ["| 参数 | 类型 | 必填 | 默认 | 说明 |", "|---|---|---|---|---|"]
                for p in params:
                    req = "✅" if p.get("required") else ""
                    default = p.get("default", "")
                    out.append(
                        f"| `{p['name']}` | {TYPE_LABEL.get(p.get('type','str'), p.get('type'))} "
                        f"| {req} | {default} | {p.get('desc','')} |"
                    )
                out.append("")
            for tip in ep.get("tips", []):
                out.append(f"> ⚠️ {tip}")
            if ep.get("tips"):
                out.append("")

    out += ["## 错误码速查", "", "| code | 含义 |", "|---|---|"]
    for code, desc in ERROR_CODES.items():
        out.append(f"| {code} | {desc.split('。')[0]} |")
    out.append("")

    (REPO / "docs" / "endpoints.md").write_text("\n".join(out), encoding="utf-8")
    print(f"endpoints.md written: {len(ENDPOINTS)} endpoints, {len(groups)} groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
