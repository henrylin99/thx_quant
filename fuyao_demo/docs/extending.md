# 扩展指南

## 新增一个接口查询页（3 分钟）

**第 1 步**：`backend/fuyao_registry.py` 的 `ENDPOINTS` 加一条记录：

```python
{
    "id": "my-new-endpoint",              # 唯一 id，决定 URL：/ep/my-new-endpoint
    "group": "特色数据",                    # 已有分组直接复用，新分组自动出现在首页
    "name": "接口显示名",
    "path": "/api/xxx/yyy",               # 扶摇原始路径（页头 chip 展示）
    "client_method": "my_new_method",     # 第 2 步要写的方法名
    "difficulty": 2,                       # 1~3 教学难度
    "doc": "一句话说明这个接口是什么、返回什么。",
    "tips": [                              # 实测中发现的坑，会渲染成「接口贴士」
        "批量上限 50 只。",
    ],
    "params": [
        {"name": "thscode", "label": "股票代码", "type": "str",
         "required": True, "placeholder": "600519.SH", "desc": "单只代码"},
        {"name": "date", "label": "日期", "type": "date_ms",
         "required": True, "desc": "前端传 YYYY-MM-DD，后端自动转北京时间零点 epoch ms"},
    ],
    "example_params": {"thscode": "600519.SH", "date": "2026-11-18"},
    "viz": "table",                        # 默认表格；需要定制图表时改这里
}
```

**第 2 步**：`backend/fuyao_client.py` 加对应方法（命名与 `client_method` 一致）：

```python
def my_new_method(self, thscode: str, date_ms: int) -> Dict[str, Any]:
    return self._request("/api/xxx/yyy", {
        "thscode": thscode,
        "date": date_ms,          # date_ms 类型已由 playground 层转好
    })
```

**第 3 步**：完成。刷新首页即可看到新接口；表单、表格、导航、JSON 页签全部自动生成。

> 原理：`/api/meta` 下发的就是这份注册表，`EndpointPage` 完全按 schema 渲染；
> `playground.py` 用 `getattr(client, client_method)` 白名单调用——所以**注册表记录 + client 方法两者名字对上**即通。

## 参数 type 速查

| type | 前端表现 | 后端处理 |
|---|---|---|
| `str` / `int` / `float` | 普通输入框 | 按 type 转换，非法值抛 `bad_param` |
| `select` | 下拉框（`options` 必填） | 原样透传 |
| `codes` | 输入框 + 批量上限提示 | 逗号分隔字符串 |
| `date_ms` | 日期选择器 | `YYYY-MM-DD` → 北京时间零点 epoch ms |
| `date_str` | 日期选择器 | 原样透传（接口直接吃该格式） |
| `bool` | 开关 | 转 bool |

## 新增定制图表组件

默认 `table` 覆盖大多数接口；需要定制可视化时：

**第 1 步**：`frontend/src/components/viz/MyViz.tsx` 新建组件：

```tsx
export default function MyViz({ data }: { data: any }) {
  // data 是上游 data 字段原样；组件内自行取 item[] 等字段
  return <div>{/* ECharts 或纯 JSX */}</div>;
}
```

**第 2 步**：`frontend/src/components/VizRouter.tsx` 注册：

```tsx
import MyViz from "./viz/MyViz";
const MAP = { /* … */ , "my-viz": MyViz };
```

**第 3 步**：注册表对应接口的 `"viz": "my-viz"`。

> 建议图表组件保持「哑组件」：只吃 `data`，不做请求、不感知业务 id——这样任何接口换 viz 都能复用。

## 调试技巧

- 后端起服务后 `curl http://127.0.0.1:5010/api/meta | jq | head` 快速核对注册表
- 业务错误会原样透出（HTTP 200 + `{ok:false, code, message}`），对照[契约手册错误码表](api-contract.md#业务错误码全集)
- client 层契约问题（时区/双命名）先看 `fuyao_client.py` 模块 docstring
