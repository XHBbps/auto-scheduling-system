# 自动排产工具 — 前端管理页面开发 Prompt

> 请使用 UI UX Max 技能，为"自动排产工具"后端系统开发一套**生产级前端管理页面**。

---

## 一、项目背景

这是一个**制造业自动排产系统**的管理后台，后端已完整实现（FastAPI + PostgreSQL），现在需要配套前端。

**核心业务**：根据销售订单的交货期，结合整机生产周期和关键零件周期，自动倒排出每台机床和每个关键零件的计划开工日期。

**用户画面**：生产计划员每天打开这个页面，查看所有订单的排产状态，关注哪些订单还没发图、哪些快到交货期了、有没有数据异常需要处理。

---

## 二、设计要求

### 整体风格
- **风格**：现代工业管理后台，简洁专业，偏深色/中性色调
- **参考**：类似 Grafana 仪表盘 + Ant Design Pro 管理后台的结合
- **配色**：主色用深蓝（#1890ff 系列），辅以灰白背景，状态色用标准语义色（绿=正常、黄=警告、红=异常）
- **字体**：中文用系统默认，数字/日期用等宽字体（增强数据可读性）
- **响应式**：优先桌面端（1920x1080），兼顾 1366x768

### 技术栈
- **Vue 3** + **Composition API** + **TypeScript**
- **Vite** 构建
- **Element Plus** 组件库（中文企业场景最成熟）
- **Vue Router** 路由
- **Axios** HTTP 请求
- **ECharts** 或 **Chart.js** 图表（仪表盘用）
- 不需要状态管理库（Pinia），数据从 API 实时拉取即可

### 开发原则
- **第一版以展示和监控为主**，除非必要不做数据写入交互
- 所有页面数据从后端 API 获取，API Base URL 配置在 `.env` 文件中
- API 统一返回格式：`{ "code": 0, "message": "success", "data": {...} }`
- `code === 0` 表示成功，非 0 弹错误提示

---

## 三、页面结构（共 7 个页面）

### 侧边栏导航结构

```
📊 排产总览            /dashboard
📋 排产列表            /schedules
📦 排产详情            /schedules/:id
⚠️ 异常管理            /issues
⚙️ 装配时长配置        /admin/assembly-times
📅 工作日历            /admin/work-calendar
🔄 数据同步            /admin/sync
```

---

## 四、各页面详细设计

### 页面 1：排产总览仪表盘 `/dashboard`

**定位**：一屏看清当前排产全貌，是每天打开的第一个页面。

**数据来源**：`GET /api/schedules?page_size=100`（拉全量数据在前端聚合统计）

**布局**（上中下三栏）：

**顶部统计卡片区**（4 个卡片一行）：
| 卡片 | 数值 | 颜色 | 计算方式 |
|------|------|------|----------|
| 订单总数 | 数字 | 蓝色 | items.length |
| 已排产 | 数字 | 绿色 | items.filter(schedule_status === "scheduled").length |
| 待发图 | 数字 | 黄色 | items.filter(schedule_status === "pending_drawing").length |
| 数据异常 | 数字 | 红色 | 从 `GET /api/issues?status=open` 获取 total |

**中部图表区**（左右两栏）：
- **左侧**：饼图 — 排产状态分布（scheduled / scheduled_stale / pending_drawing / pending_trigger / schedulable）
- **右侧**：柱状图 — 按月统计计划完工数量（按 planned_end_date 的月份分组）

**底部列表区**：
- 标题：「近期预警订单」
- 显示 warning_level !== "normal" 或 schedule_status !== "scheduled" 的前 10 条
- 列：合同编号、客户名称、产品型号、确认交货期、排产状态、异常标识
- 点击行跳转到详情页

---

### 页面 2：排产列表 `/schedules`

**定位**：核心业务页面，查看所有订单排产结果。

**API**：`GET /api/schedules`

**请求参数**：
```
page_no: int (默认 1)
page_size: int (默认 20)
contract_no: string (合同编号，模糊搜索)
customer_name: string (客户名称，模糊搜索)
product_series: string (产品系列)
product_model: string (产品型号)
order_no: string (订单编号)
schedule_status: string (排产状态，下拉选择)
warning_level: string (异常标识)
drawing_released: boolean (发图完成)
date_from: string (确认交货期开始 yyyy-MM-dd)
date_to: string (确认交货期结束 yyyy-MM-dd)
```

**返回数据**：
```json
{
  "code": 0,
  "data": {
    "total": 120,
    "page_no": 1,
    "page_size": 20,
    "items": [
      {
        "order_line_id": 101,
        "contract_no": "HT202603001",
        "customer_name": "XX客户",
        "product_series": "MC1",
        "product_model": "MC1-80",
        "product_name": "开式单点压力机",
        "quantity": 1,
        "order_no": "SO202603001",
        "confirmed_delivery_date": "2026-04-20T00:00:00",
        "drawing_released": true,
        "drawing_release_date": "2026-03-18T00:00:00",
        "trigger_date": "2026-03-26T00:00:00",
        "planned_start_date": "2026-03-27T00:00:00",
        "planned_end_date": "2026-04-20T00:00:00",
        "warning_level": "normal",
        "schedule_status": "scheduled",
        "default_flags": {}
      }
    ]
  }
}
```

**页面设计**：

**搜索区**（可折叠）：
- 第一行：合同编号、客户名称、产品系列（下拉）、产品型号
- 第二行：订单编号、排产状态（下拉: 全部/已排产/待重排/待发图/待触发/可排产）、确认交货期范围（日期选择器）
- 按钮：搜索、重置、导出Excel

**表格区**：
| 列名 | 字段 | 宽度 | 特殊渲染 |
|------|------|------|----------|
| 合同编号 | contract_no | 140px | 链接，点击跳转详情 |
| 客户名称 | customer_name | 120px | |
| 产品型号 | product_model | 100px | |
| 数量 | quantity | 60px | 居中 |
| 订单编号 | order_no | 140px | |
| 确认交货期 | confirmed_delivery_date | 100px | 格式: yyyy-MM-dd |
| 发图完成 | drawing_released | 70px | ✅ 绿色勾 / ❌ 红色叉（用 Element Plus Tag） |
| 排产状态 | schedule_status | 90px | Tag 颜色：scheduled=绿, scheduled_stale=黄, pending_drawing=黄, pending_trigger=灰, schedulable=蓝 |
| 计划开工 | planned_start_date | 100px | yyyy-MM-dd |
| 计划完工 | planned_end_date | 100px | yyyy-MM-dd |
| 整机周期 | 不在列表里 | - | - |
| 异常标识 | warning_level | 70px | normal=绿Tag, abnormal=红Tag |
| 操作 | - | 80px | 「详情」按钮 |

**排产状态中文映射**：
- `scheduled` → 已排产
- `scheduled_stale` → 待重排
- `pending_drawing` → 待发图
- `pending_trigger` → 待触发
- `schedulable` → 可排产

**导出功能**：
- 点击导出按钮，调用 `GET /api/exports/machine-schedules`（传当前筛选条件）
- 返回 xlsx 文件流，触发浏览器下载

**分页**：底部标准分页器，每页 20 条。

---

### 页面 3：排产详情 `/schedules/:id`

**定位**：单个订单的完整排产信息。

**API**：`GET /api/schedules/{orderLineId}`

**返回数据**：
```json
{
  "code": 0,
  "data": {
    "machine_schedule": {
      "order_line_id": 101,
      "contract_no": "HT202603001",
      "customer_name": "XX客户",
      "product_series": "MC1",
      "product_model": "MC1-80",
      "quantity": 1,
      "confirmed_delivery_date": "2026-04-20T00:00:00",
      "drawing_released": true,
      "trigger_date": "2026-03-26T00:00:00",
      "planned_start_date": "2026-03-27T00:00:00",
      "planned_end_date": "2026-04-20T00:00:00",
      "warning_level": "normal",
      "schedule_status": "scheduled",
      "default_flags": {}
    },
    "part_schedules": [
      {
        "assembly_name": "机身",
        "production_sequence": 1,
        "assembly_time_days": 2,
        "key_part_material_no": "30680388",
        "key_part_name": "机身铸件",
        "key_part_raw_material_desc": "机身MC1-80.1(253464)",
        "key_part_cycle_days": 15,
        "planned_start_date": "2026-03-28T00:00:00",
        "planned_end_date": "2026-04-10T00:00:00",
        "default_flags": {}
      }
    ],
    "issues": [
      {
        "id": 1,
        "issue_type": "周期异常",
        "issue_level": "medium",
        "issue_title": "关键零件周期缺失",
        "issue_detail": "按默认1天计算",
        "status": "open"
      }
    ]
  }
}
```

**页面设计**：

**顶部面包屑**：排产列表 > 排产详情 - HT202603001

**卡片 1：订单基本信息**（Description 列表，两列布局）：
- 合同编号、客户名称、产品系列、产品型号
- 数量、订单编号、确认交货期、发图状态

**卡片 2：整机排产结果**（Description 列表 + 高亮数字）：
- 排产状态（Tag）、异常标识（Tag）
- 整机周期（天）、总装天数
- 计划开工日、计划完工日
- 如果有 default_flags，显示提示："⚠️ 部分数据使用默认值"

**卡片 3：关键零件排产明细**（表格）：
| 部装名称 | 生产顺序 | 装配天数 | 关键零件料号 | 关键零件名称 | 零件周期(天) | 计划开工 | 计划完工 |
|----------|----------|----------|------------|------------|------------|---------|---------|

**卡片 4：时间线可视化**（可选，加分项）：
- 用甘特图或时间轴展示：整机周期 → 各部装的时间区间
- X 轴是日期，每个部装一行，用颜色条表示 planned_start_date ~ planned_end_date

**卡片 5：相关异常**（如果 issues 非空才显示）：
- 列表展示异常记录：类型、标题、详情、状态

**返回按钮**：左上角 ← 返回排产列表

---

### 页面 4：异常管理 `/issues`

**定位**：查看和处理系统发现的数据异常。

**API**：
- 列表：`GET /api/issues`
- 解决：`POST /api/admin/issues/{id}/resolve`（第一版只放按钮，这是唯一必要的写入操作）
- 忽略：`POST /api/admin/issues/{id}/ignore`

**请求参数**：
```
page_no, page_size, issue_type, status, biz_key, source_system
```

**返回数据**：
```json
{
  "data": {
    "total": 5,
    "items": [
      {
        "id": 1,
        "issue_type": "周期异常",
        "issue_level": "medium",
        "source_system": "scheduler",
        "biz_key": "SO202603001",
        "issue_title": "关键零件周期缺失",
        "issue_detail": "零件周期缺失，已按1天默认值计算",
        "status": "open",
        "created_at": "2026-03-17T14:00:00"
      }
    ]
  }
}
```

**页面设计**：

**筛选区**：异常类型（下拉）、状态（下拉: 全部/open/resolved/ignored）、业务键搜索

**表格**：
| 异常类型 | 异常级别 | 来源 | 业务键 | 异常标题 | 状态 | 创建时间 | 操作 |

**状态 Tag**：open=红, resolved=绿, ignored=灰

**操作列**（仅当 status=open 时显示）：
- 「已解决」按钮 → 弹 confirm 对话框 → POST /resolve
- 「忽略」按钮 → 弹 confirm 对话框 → POST /ignore

---

### 页面 5：装配时长配置 `/admin/assembly-times`

**定位**：查看各机型各部装的装配时长配置（只读展示为主）。

**API**：`GET /api/admin/assembly-times`

**请求参数**：`machine_model, product_series, assembly_name`

**返回数据**：
```json
{
  "data": [
    {
      "id": 1,
      "machine_model": "MC1-80",
      "product_series": "MC1",
      "assembly_name": "机身",
      "assembly_time_days": 2.0,
      "is_final_assembly": false,
      "production_sequence": 1,
      "is_default": false,
      "remark": null
    }
  ]
}
```

**页面设计**：

**筛选区**：机床型号（输入框）、产品系列（输入框）

**表格**：
| 机床型号 | 产品系列 | 部装名称 | 装配天数 | 是否总装 | 生产顺序 | 是否默认值 | 备注 |

- 「是否总装」用 ✅/空 表示
- 「是否默认值」用黄色 Tag "默认" 标识

---

### 页面 6：工作日历 `/admin/work-calendar`

**定位**：查看工作日/非工作日设置（只读日历视图）。

**API**：`GET /api/admin/work-calendar?month=2026-04`

**返回数据**：
```json
{
  "data": [
    {
      "id": 1,
      "calendar_date": "2026-04-05",
      "is_workday": false,
      "remark": "清明节"
    }
  ]
}
```

**页面设计**：

**月份选择器**：顶部月份切换（← 2026年4月 →）

**日历视图**（月历格子）：
- 用 Element Plus Calendar 组件或自定义网格
- 每个格子显示日期数字
- 工作日：白色背景
- 非工作日（周末默认）：浅灰背景
- 从 API 返回的非工作日：浅红背景 + 显示 remark（如"清明节"）
- 从 API 返回的调休工作日：浅绿背景 + 显示 remark（如"调休上班"）

---

### 页面 7：数据同步 `/admin/sync`

**定位**：展示同步状态概览。第一版只做展示，不做手动触发按钮。

**页面设计**（纯静态信息卡片 + 说明）：

**4 个信息卡片**：
| 数据源 | 图标 | 说明 | 接口路径 |
|--------|------|------|----------|
| 销售计划 | 📊 | 从观远平台同步销售订单数据 | POST /api/admin/sync/sales-plan |
| BOM数据 | 🏭 | 从SAP同步物料清单数据 | POST /api/admin/sync/bom |
| 生产订单 | 📦 | 从飞书多维表格同步生产订单 | POST /api/admin/sync/production-orders |
| 研究所数据 | 🔬 | 从飞书同步研究所发图数据 | POST /api/admin/sync/research |

每个卡片内容：
- 数据源名称 + 图标
- 简要说明
- 状态标记：「就绪」（绿色 Tag）
- 底部小字：对应 API 路径（供技术人员参考）

---

## 五、全局组件和布局

### Layout 布局
```
┌──────────────────────────────────────────────┐
│  Logo + 系统名称              用户头像/名称    │  ← 顶部导航栏 (64px 高，深色)
├────────┬─────────────────────────────────────┤
│        │                                     │
│ 侧边栏  │        主内容区                      │
│ 200px  │        padding: 24px               │
│ 可折叠  │                                     │
│        │                                     │
│        │                                     │
└────────┴─────────────────────────────────────┘
```

### 侧边栏菜单
- 使用 Element Plus Menu 组件
- 支持折叠为图标模式
- 当前激活项高亮

### 全局 API 封装
```typescript
// src/utils/httpClient.ts
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
})

request.interceptors.response.use(
  (response) => {
    const { code, message, data } = response.data
    if (code !== 0) {
      ElMessage.error(message || '请求失败')
      return Promise.reject(new Error(message))
    }
    return data
  },
  (error) => {
    ElMessage.error('网络请求失败')
    return Promise.reject(error)
  }
)

export default request
```

---

## 六、后端 API 完整清单

| 方法 | 路径 | 用途 | 页面 |
|------|------|------|------|
| GET | /api/schedules | 排产列表查询 | 仪表盘、列表 |
| GET | /api/schedules/{orderLineId} | 排产详情 | 详情页 |
| GET | /api/issues | 异常列表 | 仪表盘、异常页 |
| GET | /api/exports/machine-schedules | 导出整机排产Excel | 列表页 |
| GET | /api/exports/part-schedules | 导出零件排产Excel | 详情页 |
| GET | /api/admin/assembly-times | 装配时长列表 | 配置页 |
| GET | /api/admin/work-calendar?month=yyyy-MM | 工作日历 | 日历页 |
| POST | /api/admin/issues/{id}/resolve | 异常标记已解决 | 异常页 |
| POST | /api/admin/issues/{id}/ignore | 异常标记忽略 | 异常页 |

> 后端服务地址：`http://localhost:8000`
> Swagger 文档：`http://localhost:8000/docs`
> OpenAPI JSON：`http://localhost:8000/openapi.json`

---

## 七、状态枚举值中英文映射

```typescript
// 排产状态
const SCHEDULE_STATUS_MAP: Record<string, { label: string; color: string }> = {
  scheduled: { label: '已排产', color: 'success' },
  scheduled_stale: { label: '待重排', color: 'warning' },
  pending_drawing: { label: '待发图', color: 'warning' },
  pending_trigger: { label: '待触发', color: 'info' },
  schedulable: { label: '可排产', color: 'primary' },
}

// 异常标识
const WARNING_LEVEL_MAP: Record<string, { label: string; color: string }> = {
  normal: { label: '正常', color: 'success' },
  abnormal: { label: '异常', color: 'danger' },
}

// 异常状态
const ISSUE_STATUS_MAP: Record<string, { label: string; color: string }> = {
  open: { label: '待处理', color: 'danger' },
  resolved: { label: '已解决', color: 'success' },
  ignored: { label: '已忽略', color: 'info' },
}
```

---

## 八、项目结构建议

```
auto-scheduling-system/apps/web/
├── index.html
├── vite.config.ts
├── package.json
├── tsconfig.json
├── .env                        # VITE_API_BASE_URL=http://localhost:8000
├── src/
│   ├── App.vue
│   ├── main.ts
│   ├── router/
│   │   └── index.ts
│   ├── utils/
│   │   └── request.ts          # Axios 封装
│   ├── constants/
│   │   └── enums.ts            # 状态枚举映射
│   ├── layouts/
│   │   └── MainLayout.vue      # 侧边栏 + 顶栏 + 内容区
│   ├── views/
│   │   ├── Dashboard.vue       # 排产总览
│   │   ├── ScheduleList.vue    # 排产列表
│   │   ├── ScheduleDetail.vue  # 排产详情
│   │   ├── IssueList.vue       # 异常管理
│   │   ├── AssemblyTime.vue    # 装配时长配置
│   │   ├── WorkCalendar.vue    # 工作日历
│   │   └── SyncStatus.vue      # 数据同步
│   └── components/
│       ├── StatCard.vue        # 统计卡片
│       └── StatusTag.vue       # 状态标签
```

---

## 九、注意事项

1. **CORS 已配置**：后端允许所有来源，前端可直接请求 `http://localhost:8000`
2. **无需登录认证**：第一版不做用户系统
3. **日期格式**：后端返回 ISO 格式（`2026-04-20T00:00:00`），前端展示时格式化为 `yyyy-MM-dd`
4. **Decimal 字段**：后端返回的数量、天数等可能是字符串形式的小数（如 `"60.0000"`），前端注意 parseFloat
5. **空数据状态**：所有列表页在无数据时显示 Empty 占位（Element Plus 的 el-empty）
6. **前端项目放在 `auto-scheduling-system/apps/web/` 目录下**，与后端 `auto-scheduling-system/services/api/` 平级
