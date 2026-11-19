#!/usr/bin/env python3
"""Generate docs/endpoints.md from backend/fuyao_registry.py.

The registry is the single source of truth; this script renders it into a
browsable catalog page with an embedded interactive playground per endpoint:
forms are generated from the param schema, and client-side JS calls the local
fuyao_demo backend (http://127.0.0.1:5010/api/playground/<id>) directly,
rendering the JSON response as a table.

Run before `mkdocs build` in CI. Output is gitignored.
"""
import html
import json
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

INPUT_TYPE = {"int": "number", "float": "number", "date_ms": "date", "date_str": "date"}


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def playground_html(ep: dict) -> list[str]:
    """Interactive debug form for one endpoint (self-contained HTML)."""
    ep_id = esc(ep["id"])
    fields = []
    for p in ep.get("params", []):
        name = esc(p["name"])
        label = esc(p.get("label") or p["name"])
        ptype = p.get("type", "str")
        if ptype == "select":
            opts = "".join(
                f'<option value="{esc(o)}">{esc(o)}</option>' for o in p.get("options", [])
            )
            field = f'<select name="{name}">{opts}</select>'
        elif ptype == "bool":
            field = f'<select name="{name}"><option value="true">true</option><option value="false">false</option></select>'
        else:
            itype = INPUT_TYPE.get(ptype, "text")
            field = f'<input type="{itype}" name="{name}" placeholder="{esc(p.get("placeholder", ""))}">'
        req = ' <b style="color:#e53935">*</b>' if p.get("required") else ""
        fields.append(
            f'<label class="fy-field"><span>{label}{req}<br>'
            f'<small>{esc(p.get("desc", ""))}</small></span>{field}</label>'
        )
    prefill = json.dumps(ep.get("example_params", {}), ensure_ascii=False)
    return [
        f'<div class="fy-play" data-ep="{ep_id}" data-prefill="{esc(prefill)}">',
        '<div class="fy-fields">' + "".join(fields) + "</div>",
        '<div class="fy-actions">'
        f'<button class="fy-run" type="button">查询</button>'
        '<span class="fy-status"></span></div>',
        '<div class="fy-result" hidden></div>',
        "</div>",
    ]


PLAYGROUND_JS = r"""
<script>
(function () {
  var BASE_KEY = "fuyao_docs_base";
  function base() {
    var v = localStorage.getItem(BASE_KEY);
    return (v && v.trim()) || "http://127.0.0.1:5010";
  }
  // base URL 配置条（页面顶部注入一次）
  var bar = document.createElement("div");
  bar.className = "fy-basebar";
  bar.innerHTML = '<label>本地后端地址 <input id="fy-base" type="text" size="28"> '
    + '<small>（默认 http://127.0.0.1:5010，改完自动保存；需先启动 fuyao_demo）</small></label>';
  var h1 = document.querySelector("article h1");
  if (h1 && h1.parentNode) h1.parentNode.insertBefore(bar, h1.nextSibling);
  var baseInput = document.getElementById("fy-base");
  if (baseInput) {
    baseInput.value = base();
    baseInput.addEventListener("change", function () {
      localStorage.setItem(BASE_KEY, this.value.trim());
    });
  }

  function findRows(data) {
    if (Array.isArray(data) && data.length && typeof data[0] === "object") return data;
    if (data && typeof data === "object") {
      var keys = ["item", "items", "list", "data", "records", "rows"];
      for (var i = 0; i < keys.length; i++) {
        var v = data[keys[i]];
        if (Array.isArray(v) && v.length && typeof v[0] === "object") return v;
      }
      for (var k in data) {
        var v2 = data[k];
        if (Array.isArray(v2) && v2.length && typeof v2[0] === "object") return v2;
      }
    }
    return null;
  }

  function fmt(v) {
    if (v === null || v === undefined) return "";
    if (typeof v === "object") {
      var s = JSON.stringify(v);
      return s.length > 48 ? s.slice(0, 48) + "…" : s;
    }
    return String(v);
  }

  function renderTable(rows) {
    var MAXR = 50, MAXC = 15;
    var cols = [], seen = {};
    rows.slice(0, 20).forEach(function (r) {
      Object.keys(r).forEach(function (k) {
        if (!seen[k]) { seen[k] = 1; cols.push(k); }
      });
    });
    var hiddenCols = Math.max(0, cols.length - MAXC);
    cols = cols.slice(0, MAXC);
    var html = "<p>共 " + rows.length + " 行"
      + (rows.length > MAXR ? "，仅显示前 " + MAXR + " 行" : "")
      + (hiddenCols ? "，" + hiddenCols + " 列已省略" : "") + "</p>";
    html += '<div class="fy-tablewrap"><table><thead><tr>';
    cols.forEach(function (c) { html += "<th>" + fmt(c) + "</th>"; });
    html += "</tr></thead><tbody>";
    rows.slice(0, MAXR).forEach(function (r) {
      html += "<tr>";
      cols.forEach(function (c) { html += "<td>" + fmt(r[c]) + "</td>"; });
      html += "</tr>";
    });
    return html + "</tbody></table></div>";
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".fy-run");
    if (!btn) return;
    var box = btn.closest(".fy-play");
    var status = box.querySelector(".fy-status");
    var out = box.querySelector(".fy-result");
    var url = base() + "/api/playground/" + box.dataset.ep + "?";
    var params = [];
    box.querySelectorAll(".fy-fields [name]").forEach(function (el) {
      if (el.value !== "") params.push(el.name + "=" + encodeURIComponent(el.value));
    });
    btn.disabled = true; btn.textContent = "查询中…";
    status.textContent = ""; out.hidden = false;
    out.innerHTML = '<p class="fy-muted">请求中…</p>';
    fetch(url + params.join("&"))
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.ok) {
          var rows = findRows(j.data);
          if (rows) out.innerHTML = renderTable(rows);
          else out.innerHTML = '<details open><summary>返回数据（非表格结构）</summary><pre>'
            + JSON.stringify(j.data, null, 2).slice(0, 5000) + "</pre></details>";
          status.textContent = "✅ " + j.elapsed_ms + " ms";
        } else {
          out.innerHTML = '<div class="fy-err"><b>错误 ' + (j.code || "") + "</b>："
            + (j.message || "") + "</div>";
          status.textContent = "❌";
        }
      })
      .catch(function () {
        out.innerHTML = '<div class="fy-err">无法连接本地后端 <code>' + base()
          + '</code>。<br>请先启动：<code>cd fuyao_demo/backend && .venv/bin/python app.py</code>'
          + "（文档页面在 GitHub Pages 上，查询走的是你本机的后端）。</div>";
        status.textContent = "⚠️";
      })
      .finally(function () { btn.disabled = false; btn.textContent = "查询"; });
  });

  // 预填示例参数
  document.querySelectorAll(".fy-play").forEach(function (box) {
    try {
      var pre = JSON.parse(box.dataset.prefill || "{}");
      Object.keys(pre).forEach(function (k) {
        var el = box.querySelector('.fy-fields [name="' + k + '"]');
        if (el && pre[k] !== null && pre[k] !== undefined) el.value = pre[k];
      });
    } catch (e) {}
  });
})();
</script>

<style>
.fy-play { border: 1px solid var(--md-typeset-table-color, #ddd); border-radius: 8px;
  padding: .8rem 1rem; margin: .6rem 0 1.2rem; background: var(--md-code-bg-color, #f6f6f6); }
.fy-fields { display: flex; flex-wrap: wrap; gap: .6rem 1rem; }
.fy-field { display: flex; flex-direction: column; gap: .2rem; font-size: .72rem; min-width: 10rem; }
.fy-field small { opacity: .7; }
.fy-field input, .fy-field select { font-size: .8rem; padding: .25rem .4rem; min-width: 10rem; }
.fy-actions { margin-top: .6rem; display: flex; align-items: center; gap: .8rem; }
.fy-run { cursor: pointer; padding: .35rem 1.2rem; border-radius: 6px; border: none;
  background: var(--md-primary-fg-color, #3f51b5); color: #fff; font-size: .8rem; }
.fy-run:disabled { opacity: .5; }
.fy-result { margin-top: .8rem; font-size: .78rem; overflow-x: auto; }
.fy-tablewrap { max-height: 26rem; overflow: auto; }
.fy-result table { border-collapse: collapse; }
.fy-result th, .fy-result td { border: 1px solid var(--md-typeset-table-color, #ddd);
  padding: .25rem .5rem; white-space: nowrap; }
.fy-result th { position: sticky; top: 0; background: var(--md-code-bg-color, #eee); }
.fy-err { border-left: 4px solid #e53935; padding: .5rem .8rem; background: rgba(229,57,53,.08); }
.fy-muted { opacity: .6; }
.fy-basebar { font-size: .75rem; padding: .5rem .8rem; margin: .8rem 0;
  border: 1px dashed var(--md-typeset-table-color, #bbb); border-radius: 6px; }
.fy-basebar input { font-size: .75rem; padding: .15rem .3rem; }
</style>
"""


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
        '!!! tip "在线调试"',
        "    每个接口下方有「参数表单 + 查询按钮」——点击后直接请求你本机运行的 fuyao_demo 后端，"
        "返回数据自动渲染成表格。需要先启动后端：`cd backend && .venv/bin/python app.py`。",
        "",
    ]
    for group, eps in groups.items():
        out += [f"## {group}（{len(eps)}）", ""]
        for ep in eps:
            out += [
                f"### {ep['name']}",
                "",
                f"`{ep['path']}` · 难度 {'★' * ep.get('difficulty', 1)} · "
                f"可视化：{VIZ_LABEL.get(ep.get('viz', 'table'), ep.get('viz'))}",
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
            out += playground_html(ep)
            for tip in ep.get("tips", []):
                out.append(f"> ⚠️ {tip}")
            if ep.get("tips"):
                out.append("")

    out += ["## 错误码速查", "", "| code | 含义 |", "|---|---|"]
    for code, desc in ERROR_CODES.items():
        out.append(f"| {code} | {desc.split('。')[0]} |")
    out += ["", PLAYGROUND_JS, ""]

    (REPO / "docs" / "endpoints.md").write_text("\n".join(out), encoding="utf-8")
    print(f"endpoints.md written: {len(ENDPOINTS)} endpoints, {len(groups)} groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
