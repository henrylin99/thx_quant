"""扶摇（同花顺官方金融数据 API）REST 客户端 —— 教学精简版。

从 quantitative_analysis 项目的 fuyao_client.py 精简移植，保留全部
契约处理经验（认证 / 信封 / 时区 / 节流），去掉 dump 下载等重逻辑。

契约要点（也是本项目每个接口页「接口贴士」的教学素材）：
- 认证：请求头 ``X-api-key``；key 从环境变量 FUYAO_API_KEY 读取
- 响应信封：``{code, message, data}``，code != 0 视为业务错误
  （4001 限频 / 1002 无效代码或非交易日 / 1003 超批量 / 5003 未披露报告期）
- 时间口径：所有 *ms 字段为北京时间零点的 epoch ms，统一用
  beijing_ms_to_ymd 解析（按 UTC 解析会偏一天）
- 字段双命名：快照接口实测返回 high_price/low_price/prev_price，
  官方文档为 highest_price/lowest_price/prev_close_price，取值时两者都试
- 节流：单请求间隔默认 0.12s（实测 200+ 连发未触发 4001）
"""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests
from dotenv import load_dotenv

BEIJING_TZ = timezone(timedelta(hours=8))

BASE_URL = "https://fuyao.aicubes.cn"
API_KEY_ENV = "FUYAO_API_KEY"
DEFAULT_THROTTLE_SECONDS = 0.12
DEFAULT_TIMEOUT_SECONDS = 30

#: 快照单页条数（6000 覆盖全市场）
SNAPSHOT_PAGE_SIZE = 6000
#: thscodes 批量接口单次上限（快照批量/估值快照）
BATCH_LIMIT = 100
#: 个股异动原因按股票查询单次上限
ANOMALY_BATCH_LIMIT = 50

FINANCIAL_STATEMENT_ENDPOINTS = {
    "income": "income-statements",
    "balance_sheet": "balance-sheets",
    "cash_flow": "cash-flow-statements",
}


def beijing_ms_to_ymd(value_ms: Optional[float]) -> Optional[str]:
    """北京时间零点的 epoch ms → YYYYMMDD。

    扶摇所有日期字段都是北京时间零点，按 UTC 解析会得到前一天。
    """
    if value_ms is None or value_ms != value_ms:  # NaN 防御
        return None
    try:
        dt = datetime.fromtimestamp(float(value_ms) / 1000.0, tz=BEIJING_TZ)
    except (OverflowError, OSError, ValueError):
        return None
    return dt.strftime("%Y%m%d")


def ymd_to_beijing_ms(date_str: str) -> Optional[int]:
    """YYYY-MM-DD 或 YYYYMMDD → 北京时间零点的 epoch ms（接口 date_ms 参数口径）。"""
    text = (date_str or "").strip().replace("-", "")
    try:
        dt = datetime.strptime(text, "%Y%m%d").replace(tzinfo=BEIJING_TZ)
    except ValueError:
        return None
    return int(dt.timestamp() * 1000)


class FuyaoError(RuntimeError):
    """扶摇业务错误（响应信封 code != 0 或 HTTP 非 2xx）。"""

    def __init__(self, code: Any, message: str):
        super().__init__(f"fuyao error code={code}: {message}")
        self.code = code
        self.message = message

    @property
    def is_rate_limited(self) -> bool:
        return str(self.code) == "4001"

    @property
    def is_invalid_code(self) -> bool:
        return str(self.code) == "1002"


class FuyaoClient:
    """扶摇 REST 客户端：请求节流 + 信封解包 + 各数据端点封装。

    客户端不做字段换算/归一化，只把端点返回的 data 原样交给调用方——
    教学项目刻意保留原始响应结构，方便对照官方文档学习。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        throttle_seconds: Optional[float] = None,
        session: Optional[requests.Session] = None,
    ):
        load_dotenv()
        self.api_key = (api_key if api_key is not None else os.getenv(API_KEY_ENV, "")).strip()
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.timeout = timeout
        self.throttle_seconds = (
            throttle_seconds if throttle_seconds is not None else DEFAULT_THROTTLE_SECONDS
        )
        self._session = session or requests.Session()
        self._throttle_lock = threading.Lock()
        self._last_request_monotonic = 0.0

    # ---- 基础请求 ----

    def _throttle(self) -> None:
        if self.throttle_seconds <= 0:
            return
        with self._throttle_lock:
            wait = self._last_request_monotonic + self.throttle_seconds - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_request_monotonic = time.monotonic()

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if not self.api_key:
            raise FuyaoError("no_key", f"未配置 {API_KEY_ENV}，请在 backend/.env 中设置后重试")
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        self._throttle()
        try:
            resp = self._session.get(
                f"{self.base_url}{path}",
                headers={"X-api-key": self.api_key},
                params=clean_params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise FuyaoError("network", f"扶摇请求失败: {exc}") from exc
        if resp.status_code != 200:
            raise FuyaoError(resp.status_code, f"扶摇 HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise FuyaoError("bad_json", f"扶摇响应不是 JSON: {resp.text[:200]}") from exc
        code = payload.get("code")
        if code != 0:
            raise FuyaoError(code, payload.get("message", ""))
        return payload.get("data")

    # ---- 行情快照 ----

    def snapshot_page(
        self,
        limit: int = SNAPSHOT_PAGE_SIZE,
        offset: int = 0,
        thscodes: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """A 股全市场实时快照，分页或按 thscodes 批量（≤100）。"""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if thscodes:
            params["thscodes"] = ",".join(thscodes[:BATCH_LIMIT])
            params.pop("limit")
            params.pop("offset")
        return self._get("/api/a-share/prices/snapshot", params) or {}

    def price_snapshot_batch(self, thscodes: Sequence[str]) -> List[Dict[str, Any]]:
        """按代码批量拉实时快照（单次 ≤100 只）。"""
        data = self.snapshot_page(thscodes=thscodes)
        return data.get("item") or []

    def index_snapshot(self, thscodes: Sequence[str]) -> Tuple[List[Dict[str, Any]], Optional[int]]:
        """指数实时快照（沪深交易所指数 + 同花顺板块指数，无北交所）。

        未知代码会导致整批 1002 连坐，调用方需先过滤 .BJ 等不支持代码；
        批量上限 100 只，超量由调用方分批。
        """
        data = self._get(
            "/api/a-share-index/prices/snapshot",
            {"thscodes": ",".join(thscodes[:BATCH_LIMIT])},
        )
        items = data.get("item") or []
        ts = data.get("timestamp")
        return items, int(ts) if isinstance(ts, (int, float)) else None

    # ---- 指数目录与成分 ----

    def ths_index_catalog(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """同花顺指数目录（tag: industry=行业 / cn_concept=概念，可空=全部）。"""
        data = self._get("/api/a-share-index/catalog/ths-index-list", {"tag": tag})
        return data.get("item") or []

    def ths_index_constituents(self, thscode: str) -> List[Dict[str, Any]]:
        """同花顺指数成分股（item: {thscode, ticker, name}）。"""
        data = self._get(
            "/api/a-share-index/constituents/ths-stock-list",
            {"thscode": thscode},
        )
        return data.get("item") or []

    # ---- 历史日K ----

    def historical_kline(
        self,
        thscode: str,
        start_ms: Optional[int] = None,
        end_ms: Optional[int] = None,
        interval: str = "1d",
        adjust: str = "none",
    ) -> List[Dict[str, Any]]:
        """单标的历史K线。adjust 锁定 none（服务端前复权有逐日漂移，禁用）。

        服务端单次窗口 ≤10 年，超长窗口由调用方分片。
        """
        data = self._get(
            "/api/a-share/prices/historical",
            {
                "thscode": thscode,
                "interval": interval,
                "adjust": adjust,
                "start": start_ms,
                "end": end_ms,
            },
        )
        return data.get("item") or []

    # ---- 财务 ----

    def financial_statement(
        self,
        table: str,
        thscode: str,
        limit: int = 20,
        period: str = "quarterly",
    ) -> List[Dict[str, Any]]:
        """单标的财务报表（income/balance_sheet/cash_flow），单次 ≤20 期。"""
        endpoint = FINANCIAL_STATEMENT_ENDPOINTS.get(table)
        if not endpoint:
            raise FuyaoError("bad_table", f"未知财务表: {table}（income/balance_sheet/cash_flow）")
        data = self._get(
            f"/api/a-share/financials/{endpoint}",
            {"thscode": thscode, "period": period, "limit": limit},
        )
        return data.get("item") or []

    def valuations_snapshot(self, thscodes: Sequence[str]) -> List[Dict[str, Any]]:
        """估值快照（pe_ttm/pe_mrq/pb_mrq/ps_ttm/pcf_ttm），单次 ≤100 只。"""
        data = self._get(
            "/api/a-share/valuations/snapshot",
            {"thscodes": ",".join(thscodes[:BATCH_LIMIT])},
        )
        return data.get("item") or []

    # ---- 日历与特色数据 ----

    def trading_days(self) -> List[Dict[str, Any]]:
        """交易日历（固定近一年窗口，item: {date_ms, date}）。"""
        data = self._get("/api/a-share/calendar/trading-days")
        return data.get("item") or []

    def dragon_tiger_list(
        self, board_type: str = "all", date: Optional[str] = None
    ) -> Dict[str, Any]:
        """龙虎榜（board_type: all/org/hot_money；date 可空=最近发布日）。"""
        return self._get(
            "/api/a-share/special-data/dragon-tiger-list",
            {"board_type": board_type, "date": date},
        ) or {}

    def short_term_benchmark(self, date: Optional[str] = None) -> Dict[str, Any]:
        """盘前竞价短线风向标（date 可空；支持一年内历史）。"""
        return self._get(
            "/api/a-share/auction/short-term-benchmark",
            {"date": date},
        ) or {}

    def auction_snapshot(
        self, thscodes: Sequence[str], stage: Optional[str] = None
    ) -> Dict[str, Any]:
        """A 股集合竞价快照（thscodes 单次 ≤100；stage: live/final）。

        注意：文档写 finallive，实测合法值为 live（实时）/ final（终态）。
        """
        params: Dict[str, Any] = {"thscodes": ",".join(thscodes[:BATCH_LIMIT])}
        if stage:
            params["stage"] = stage
        return self._get("/api/a-share/auction/snapshot", params) or {}

    def auction_stock_opportunities(
        self,
        date: Optional[str] = None,
        warn_types: Optional[Sequence[str]] = None,
        market: Optional[str] = None,
        exclude_st: Optional[bool] = None,
        thscodes: Optional[Sequence[str]] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Dict[str, Any]:
        """集合竞价个股机会筛选（date yyyy-MM-dd 须在可用日期集合内；size 1~20）。"""
        params: Dict[str, Any] = {
            "date": date,
            "warn_types": ",".join(warn_types) if warn_types else None,
            "market": market,
            "exclude_st": None if exclude_st is None else ("true" if exclude_st else "false"),
            "thscodes": ",".join(thscodes[:ANOMALY_BATCH_LIMIT]) if thscodes else None,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "size": size,
        }
        return self._get("/api/a-share/special-data/auction-stock-opportunities", params) or {}

    def auction_opportunity_dates(self) -> Dict[str, Any]:
        """集合竞价可选交易日期（dates 升序 yyyy-MM-dd；latest_date=默认查询日）。"""
        return self._get("/api/a-share/special-data/auction-opportunity-dates") or {}

    def limit_up_pool(
        self,
        date_ms: Optional[int] = None,
        page: int = 1,
        size: int = 100,
        sort_field: str = "continue_day_cnt",
        sort_dir: str = "desc",
    ) -> Dict[str, Any]:
        """A 股涨停股票池（date_ms 为北京时间零点 epoch ms，可空=最近交易日）。

        非交易日不传 date_ms 会返回空列表（total=0），由调用方回退最近交易日。
        """
        return self._get(
            "/api/a-share/special-data/limit-up-pool",
            {
                "date_ms": date_ms,
                "page": page,
                "size": size,
                "sort_field": sort_field,
                "sort_dir": sort_dir,
            },
        ) or {}

    def limit_down_pool(
        self,
        date_ms: Optional[int] = None,
        page: int = 1,
        size: int = 100,
    ) -> Dict[str, Any]:
        """A 股跌停股票池（date_ms 口径同涨停池）。"""
        return self._get(
            "/api/a-share/special-data/limit-down-pool",
            {"date_ms": date_ms, "page": page, "size": size},
        ) or {}

    def limit_break_pool(
        self,
        date_ms: Optional[int] = None,
        page: int = 1,
        size: int = 100,
    ) -> Dict[str, Any]:
        """A 股炸板股票池（曾涨停后开板；date_ms 口径同涨停池）。"""
        return self._get(
            "/api/a-share/special-data/limit-break-pool",
            {"date_ms": date_ms, "page": page, "size": size},
        ) or {}

    def limit_up_ladder(self) -> Dict[str, Any]:
        """连板天梯矩阵（近 30 个交易日）。

        data.item[].boards 键：two_board/three_board/…/seven_over，
        每档为个股列表（thscode/ticker/name/board_num/seal_nextday/sign_level）。
        """
        return self._get("/api/a-share/special-data/limit-up-ladder") or {}

    def hot_stock_list(self, period: str = "day") -> List[Dict[str, Any]]:
        """同花顺热股榜（period: day/hour；Top30）。"""
        data = self._get("/api/a-share/special-data/hot-stock-list", {"period": period})
        return data.get("item") or []

    def skyrocket_list(self, period: str = "day") -> List[Dict[str, Any]]:
        """同花顺热股飙升榜（热度飙升最快；period: day/hour；Top30）。"""
        data = self._get("/api/a-share/special-data/skyrocket-list", {"period": period})
        return data.get("item") or []

    def hot_stock_list_history(self, date: str) -> Dict[str, Any]:
        """历史热股排行（date: yyyy-MM-dd，只支持一年内）。

        date 格式非法返回 1002，超出一年返回 1003。
        """
        return self._get(
            "/api/a-share/special-data/hot-stock-list-history",
            {"date": date},
        ) or {}

    def hot_stock_rank_trend(self, thscode: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """个股热榜排名走势（窗口与日期均限一年内，start>end 服务端 1004）。"""
        data = self._get(
            "/api/a-share/special-data/hot-stock-rank-trend",
            {"thscode": thscode, "start_date": start_date, "end_date": end_date},
        )
        return data.get("item") or []

    def anomaly_analysis_list(self, tag_codes: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
        """当日个股异动原因列表（tag_codes 多值 OR）。

        合法标签：LIMIT_UP/LIMIT_DOWN/SHARP_RISE/SHARP_FALL/RAPID_RALLY/RAPID_DECLINE；
        当日数据暂不可用时服务端返回 3002。
        """
        data = self._get(
            "/api/a-share/special-data/anomaly-analysis-list",
            {"tag_codes": ",".join(tag_codes) if tag_codes else None},
        )
        return data.get("item") or []

    def anomaly_analysis_stock(self, thscodes: Sequence[str]) -> List[Dict[str, Any]]:
        """按代码批量查询当日个股异动原因（去重前 ≤50 个）。"""
        data = self._get(
            "/api/a-share/special-data/anomaly-analysis-stock",
            {"thscodes": ",".join(thscodes[:ANOMALY_BATCH_LIMIT])},
        )
        return data.get("item") or []

    def abnormal_monitor_list(
        self, state: str = "current", page: int = 1, size: int = 30
    ) -> Dict[str, Any]:
        """异动股票监控名单（state: current/history；size ≤30，分页从 1 起）。"""
        return self._get(
            "/api/a-share/special-data/abnormal-monitor-list",
            {"state": state, "page": page, "size": size},
        ) or {}

    def ticker_search(
        self, query: str, asset_type: str = "a-share", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """标的检索（名称/代码模糊匹配，用于搜索联想）。"""
        data = self._get(
            "/api/meta/tickers/search",
            {"q": query, "asset_type": asset_type, "limit": limit},
        )
        return data.get("item") or []

    # ---- 基金 ----
    # 契约要点：
    # - 单只查询，thscodes 逗号多值不支持；场内快照 ETF/LOF，历史日线仅 ETF
    # - 窗口 ≤5 自然年（1003）；场外基金走场内接口返回 3004
    # - 3001 标的不存在 / 3002 数据未就绪

    def fund_profile(self, thscode: str) -> List[Dict[str, Any]]:
        """基金基本资料（fund_name/estab_date/mgmt_name/fund_scale 等）。"""
        data = self._get("/api/fund/profile/detail", {"thscode": thscode})
        return data.get("item") or []

    def fund_market_snapshot(self, thscode: str) -> List[Dict[str, Any]]:
        """场内基金实时快照（仅 ETF/LOF，单只）。"""
        data = self._get("/api/fund/market/snapshot", {"thscode": thscode})
        return data.get("item") or []

    def fund_historical(self, thscode: str, start_ms: int, end_ms: int, interval: str = "1d") -> List[Dict[str, Any]]:
        """ETF 前复权历史日线（仅 ETF；窗口 ≤5 自然年由调用方保证）。"""
        data = self._get(
            "/api/fund/market/historical",
            {
                "thscode": thscode,
                "interval": interval,
                "start": start_ms,
                "end": end_ms,
            },
        )
        return data.get("item") or []

    def fund_nav(
        self,
        thscode: str,
        range: Optional[str] = None,
        nav_type: str = "unit,adj",
    ) -> List[Dict[str, Any]]:
        """基金净值序列（range: week..fyear，缺省仅最新一条；nav_type: unit/adj/unit,adj）。"""
        data = self._get(
            "/api/fund/performance/nav",
            {"thscode": thscode, "range": range, "nav_type": nav_type},
        )
        return data.get("item") or []

    def fund_returns(self, thscode: str) -> Dict[str, Any]:
        """基金区间收益与同类排名（return_*、peer_average_*、rank_*）。"""
        return self._get("/api/fund/performance/returns", {"thscode": thscode}) or {}

    def fund_drawdowns(self, thscode: str) -> Dict[str, Any]:
        """基金各区间最大回撤（week..now；nowyear=今年以来 / now=成立以来）。"""
        return self._get("/api/fund/performance/drawdowns", {"thscode": thscode}) or {}

    def fund_holdings(self, thscode: str) -> Dict[str, Any]:
        """基金最新重仓持仓：顶层汇总（股票/债券/基金占比、集中度）+ item 明细。"""
        return self._get("/api/fund/portfolio/holdings", {"thscode": thscode}) or {}

    def fund_holders_detail(self, thscode: str, merge_scope: str = "all") -> List[Dict[str, Any]]:
        """基金持有人结构（机构/个人占比、户数；merge_scope: all/merged/separate）。"""
        data = self._get(
            "/api/fund/holders/detail", {"thscode": thscode, "merge_scope": merge_scope}
        )
        return data.get("item") or []

    def fund_holders_top(self, thscode: str, limit: int = 10) -> List[Dict[str, Any]]:
        """基金前十大持有人（limit ≤10）。"""
        data = self._get("/api/fund/holders/top", {"thscode": thscode, "limit": limit})
        return data.get("item") or []

    def fund_asset_allocation(self, thscode: str) -> List[Dict[str, Any]]:
        """基金历史资产配置（报告期股票/债券/存款/其他占比）。"""
        data = self._get("/api/fund/portfolio/asset-allocation", {"thscode": thscode})
        return data.get("item") or []

    def fund_industry_allocation(self, thscode: str) -> List[Dict[str, Any]]:
        """基金历史行业配置（report_period 如 2026Q2 + industry_name/ratio_pct）。"""
        data = self._get("/api/fund/portfolio/industry-allocation", {"thscode": thscode})
        return data.get("item") or []

    def fund_manager_detail(self, manager_id: str) -> List[Dict[str, Any]]:
        """基金经理详情（manager_id 可从基金基本资料 manager_info 获取）。"""
        data = self._get("/api/fund/managers/detail", {"manager_id": manager_id})
        return data.get("item") or []

    def fund_diagnostics(self, thscode: str) -> List[Dict[str, Any]]:
        """基金诊断详情（诊断维度/同类对比/韧性指标，上游结构原样透传）。"""
        data = self._get("/api/fund/diagnostics/detail", {"thscode": thscode})
        return data.get("item") or []

    def fund_dividends(self, thscode: str) -> Dict[str, Any]:
        """基金历史分红（dividend_count/dividend_total + 每条每 10 份分红与日期）。"""
        return self._get("/api/fund/corporate-actions/dividends", {"thscode": thscode}) or {}

    def fund_company(self, company_id: str) -> List[Dict[str, Any]]:
        """基金公司详情（company_id 来自基金基本资料，不能用名称代替）。"""
        data = self._get("/api/fund/companies/detail", {"company_id": company_id})
        return data.get("item") or []
