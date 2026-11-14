"""教学项目通用代理路由 —— 注册表驱动的核心。

只有两个端点：
- GET /api/meta          下发接口注册表（分组/参数 schema/错误码表）
- GET /api/playground/<endpoint_id>   按注册表白名单调用扶摇接口

设计要点（教学价值）：
- 参数白名单：只放行注册表里声明的参数，杜绝任意参数透传
- 类型转换集中在这里：date_ms 在后端统一转北京时间零点 epoch ms
- 错误信封原样透出：FuyaoError 的 code/message 直接给前端渲染成教学卡片
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request

from fuyao_client import FuyaoClient, FuyaoError, ymd_to_beijing_ms
from fuyao_registry import get_endpoint, meta_for_frontend

bp = Blueprint("playground", __name__)

_client = FuyaoClient()


def _ok(data: Any, elapsed_ms: int) -> Any:
    return jsonify({"ok": True, "elapsed_ms": elapsed_ms, "data": data})


def _error(code: Any, message: str, status: int = 200) -> Any:
    # 业务错误仍返回 200（错误信封本身就是教学素材），HTTP 层错误用 4xx/5xx
    return jsonify({"ok": False, "code": str(code), "message": message}), status


def _convert_param(pdef: Dict[str, Any], raw: Any) -> Any:
    """按注册表类型把表单原始值转成 client 方法入参。"""
    ptype = pdef.get("type", "str")
    if raw is None or raw == "":
        return None
    if ptype == "int":
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            raise FuyaoError("bad_param", f"参数 {pdef['name']} 需要整数，收到: {raw!r}")
    if ptype == "float":
        try:
            return float(raw)
        except (TypeError, ValueError):
            raise FuyaoError("bad_param", f"参数 {pdef['name']} 需要数字，收到: {raw!r}")
    if ptype == "bool":
        return str(raw).lower() in ("1", "true", "yes", "on")
    if ptype == "date_ms":
        ms = ymd_to_beijing_ms(str(raw))
        if ms is None:
            raise FuyaoError("bad_param", f"参数 {pdef['name']} 日期格式非法: {raw!r}（应为 YYYY-MM-DD）")
        return ms
    # str / select / codes / date_str 均按字符串透传
    return str(raw)


@bp.route("/api/meta", methods=["GET"])
def meta():
    return jsonify(meta_for_frontend())


@bp.route("/api/playground/<endpoint_id>", methods=["GET"])
def playground(endpoint_id: str):
    ep = get_endpoint(endpoint_id)
    if ep is None:
        return _error("not_found", f"未知接口: {endpoint_id}", 404)

    raw_params: Dict[str, str] = request.args.to_dict()
    kwargs: Dict[str, Any] = {}
    for pdef in ep.get("params", []):
        name = pdef["name"]
        if name in raw_params:
            try:
                converted = _convert_param(pdef, raw_params[name])
            except FuyaoError as exc:
                return _error(exc.code, exc.message)
            if converted is not None:
                kwargs[name] = converted

    # 必填参数校验
    for pdef in ep.get("params", []):
        if pdef.get("required") and pdef["name"] not in kwargs:
            return _error("missing_param", f"缺少必填参数: {pdef['name']}（{pdef.get('label', '')}）")

    started = time.monotonic()
    try:
        method = getattr(_client, ep["client_method"])
        data = method(**kwargs)
    except FuyaoError as exc:
        return _error(exc.code, exc.message)
    except TypeError as exc:
        return _error("bad_request", f"参数不匹配: {exc}")
    elapsed_ms = int((time.monotonic() - started) * 1000)
    return _ok(data, elapsed_ms)
