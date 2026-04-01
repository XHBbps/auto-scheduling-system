from collections import defaultdict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.common.auth import AUTH_SESSION_SECURITY_SCHEME_NAME
from app.config import settings


OPENAPI_TAGS = [
    {"name": "排产查询", "description": "排产总览、整机排产列表、零件排产列表和订单排产详情查询接口。"},
    {"name": "异常查询", "description": "异常列表与异常筛选项查询接口。"},
    {"name": "导出", "description": "排产列表与零件排产结果导出接口，支持 Excel / CSV 文件流。"},
    {"name": "手动同步", "description": "销售计划、BOM、生产订单、研究所数据的手动同步与调度控制接口。"},
    {"name": "排产管理", "description": "批量排产、单订单零件排产、snapshot 重建与观测接口。"},
    {"name": "装配时长配置", "description": "装配时长基准的查询、保存与删除接口。"},
    {"name": "整机周期基准", "description": "整机周期基准维护与重建接口。"},
    {"name": "零件周期基准", "description": "零件周期基准维护接口。"},
    {"name": "工作日历管理", "description": "工作日历、排产日历分布与日明细接口。"},
    {"name": "异常处理", "description": "异常记录处理接口，包括解决与忽略。"},
    {"name": "同步任务日志", "description": "同步任务日志列表、详情和删除接口。"},
    {"name": "用户认证", "description": "用户登录、登出与会话状态查询接口。"},
    {"name": "外源数据-销售计划订单行", "description": "销售计划源数据查询与组织筛选项接口。"},
    {"name": "外源数据-BOM物料清单", "description": "BOM 明细列表、树结构与懒加载子节点接口。"},
    {"name": "外源数据-生产订单历史", "description": "生产订单历史源数据查询接口。"},
    {"name": "外源数据-整机周期历史", "description": "整机周期历史源数据查询接口。"},
]


OPENAPI_DESCRIPTION = """
## 接口文档说明

这是自动排产系统的后端 Swagger / OpenAPI 文档页，用于查看、联调和验证当前后端接口。

### 返回结构约定

- 大多数 JSON 接口统一返回：`{ code, message, data }`
- `code = 0` 表示成功
- 文件导出接口直接返回二进制文件流，不走 JSON 包装

### 受保护接口认证

以下接口默认需要先通过 `/api/auth/login` 完成账号密码登录，并携带会话 Cookie：

- `/api/admin/*`
- `/api/data/*`
- `/api/exports/*`
- `/api/dashboard/overview`
- `/api/schedules*`
- `/api/part-schedules*`
- `/api/issues*`

### Cookie 联调步骤

1. 调用 `POST /api/auth/login`，传入登录账号和登录密码
2. 确认响应头 `Set-Cookie` 已写入用户会话 Cookie
3. 使用同一浏览器会话或同一个 Cookie Jar 继续调用受保护接口
4. 可通过 `GET /api/auth/session` 检查当前会话状态
5. 联调结束后调用 `POST /api/auth/logout` 注销会话

### 非浏览器客户端说明

- Postman、curl、脚本联调时，需要先调登录接口保存 Cookie
- 后续请求继续携带该 Cookie；不能再只传旧版管理员令牌

### 入参阅读方式

- `Authorize` / `Security`：表示认证信息（如用户会话 Cookie）
- `Parameters`：表示路径参数、查询参数、Cookie 参数
- `Request body`：表示 JSON 请求体
- 每个接口说明中还会按“认证信息 / 路径参数 / 查询参数 / 请求体”再做一层结构化整理

### 推荐使用方式

1. 先在本页确认接口路径、请求参数和请求体结构
2. 联调前优先对照前端页面实际调用的接口
3. 发生数据状态异常时，优先查看同步、排产和 snapshot 相关接口
"""


OPENAPI_PARAMETER_DESCRIPTIONS = {
    "user_session": "用户会话 Cookie。调用受保护的查询、管理、外源数据和导出接口时必须携带。",
    "page_no": "分页页码，从 1 开始。",
    "page_size": "每页返回的记录数。",
    "sort_field": "排序字段名；可选字段请参考接口说明或前端筛选项。",
    "sort_order": "排序方向；通常为 asc（升序）或 desc（降序）。",
    "record_id": "要操作的基准配置记录 ID。",
    "issue_id": "异常记录 ID。",
    "log_id": "同步任务日志记录 ID。",
    "order_line_id": "销售订单行 ID。",
    "contract_no": "合同号；支持精确匹配或关键字筛选。",
    "customer_name": "客户名称；支持关键字筛选。",
    "product_series": "产品系列筛选值。",
    "product_model": "机型筛选值。",
    "plant": "工厂编码筛选值；用于区分同物料在不同工厂下的 BOM、快照、查询与导出结果。",
    "machine_model": "整机机型筛选值。",
    "order_no": "销售订单号筛选值。",
    "schedule_status": "排产状态筛选值；如 pending_delivery（待交期）、pending_drawing（待发图）、pending_trigger（待触发）、schedulable（可排产）、scheduled（已排产）等。",
    "schedule_bucket": "排产桶筛选；如 unscheduled（未排产）、risk（风险订单）。",
    "warning_level": "预警等级筛选值。",
    "drawing_released": "是否已发图；true 表示已发图，false 表示未发图。",
    "date_from": "日期范围开始值，格式通常为 yyyy-MM-dd。",
    "date_to": "日期范围结束值，格式通常为 yyyy-MM-dd。",
    "assembly_name": "部装名称或装配名称筛选值。",
    "part_material_no": "零件物料号筛选值。",
    "key_part_name": "关键零件名称筛选值。",
    "key_part_material_no": "关键零件物料号筛选值。",
    "issue_type": "异常类型筛选值。",
    "biz_key": "业务主键筛选值，当前通常为订单行 ID。",
    "source_system": "来源系统筛选值，如 sales_plan、bom、research。",
    "status": "状态筛选值；不同接口含义不同，请结合接口 summary 查看。",
    "job_type": "同步任务类型筛选值。",
    "material_no": "物料号筛选值。",
    "machine_material_no": "整机物料号筛选值。",
    "bom_component_no": "BOM 子件物料号筛选值。",
    "part_type": "零件类型或零件类别筛选值。",
    "core_part_name": "核心零件名称筛选值。",
    "is_active": "是否启用该基准；true 为启用，false 为停用。",
    "window_days": "快照重建窗口天数；系统会重建最近 N 天范围内的排产快照。",
    "failure_kind": "补数失败类型筛选值。",
    "source": "数据来源或任务来源筛选值。",
    "production_order_no": "生产订单号筛选值。",
    "order_status": "生产订单状态筛选值。",
    "business_group": "事业部筛选值。",
    "sales_branch_company": "销售分公司筛选值。",
    "sales_sub_branch": "销售子公司或办事处筛选值。",
    "parent_material_no": "父级物料号；用于查询指定 BOM 节点的下级子节点。",
    "offset": "懒加载子节点时的起始偏移量。",
    "limit": "懒加载子节点时本次最多返回的节点数量。",
    "export_format": "导出文件格式；xlsx 表示 Excel，csv 表示 CSV 文本。",
    "month": "要查询的月份，格式 yyyy-MM。",
    "date": "要查看明细的日历日期，格式 yyyy-MM-dd。",
}


OPENAPI_SCHEMA_DESCRIPTIONS = {
    "HTTPValidationError": "请求参数或请求体校验失败时返回的标准错误结构。",
    "ValidationError": "单个字段的校验失败明细。",
}


OPENAPI_SCHEMA_FIELD_DESCRIPTIONS = {
    "HTTPValidationError": {
        "detail": "校验失败明细列表，每一项对应一个入参错误。",
    },
    "ValidationError": {
        "loc": "出错字段路径，依次表示 body/query/path 等定位信息。",
        "msg": "校验失败提示信息。",
        "type": "校验错误类型标识。",
        "input": "触发校验失败的原始入参值。",
        "ctx": "错误上下文附加信息，有时会包含额外约束参数。",
    },
}


OPENAPI_FIELD_DESCRIPTIONS = {
    **OPENAPI_PARAMETER_DESCRIPTIONS,
    "id": "记录主键 ID。",
    "order_line_ids": "要执行操作的销售订单行 ID 列表。",
    "force_rebuild": "是否强制重建相关排产结果；当前版本通常默认开启。",
    "start_time": "同步窗口开始时间；为空时按系统默认增量窗口执行。",
    "end_time": "同步窗口结束时间；为空时按系统默认增量窗口执行。",
    "mode": "执行模式；不同接口可选值请参考该请求体的说明。",
    "enabled": "是否启用自动调度；true 表示启用，false 表示停用。",
    "ids": "要批量处理的记录 ID 列表。",
    "plant": "工厂编码。",
    "remark": "备注说明。",
    "product_name": "产品名称。",
    "quantity": "数量。",
    "order_type": "订单类型。",
    "line_total_amount": "订单行金额。",
    "order_date": "订单日期。",
    "business_group": "事业部。",
    "custom_no": "定制号。",
    "sales_person_name": "销售人员姓名。",
    "sales_branch_company": "销售分公司。",
    "sales_sub_branch": "销售子公司或办事处。",
    "sap_code": "SAP 编码。",
    "sap_line_no": "SAP 行号。",
    "confirmed_delivery_date": "确认交期。",
    "drawing_release_date": "发图日期。",
    "custom_requirement": "定制要求。",
    "review_comment": "评审备注。",
    "trigger_date": "排产触发日期；当前口径等同基于确认交期和整机周期倒排出的最晚开工日，不单独扣减总装时长。",
    "machine_cycle_days": "整机主周期（天）；当前口径用于从确认交期倒排 trigger_date / planned_start_date，不包含单独预留的总装缓冲说明。",
    "machine_assembly_days": "整机总装时长（天）；当前口径单独存储，主要用于零件排产阶段从整机交期向前预留总装窗口。",
    "planned_start_date": "计划开工日期。",
    "planned_end_date": "计划完工日期。",
    "default_flags": "默认值命中标记集合，用于说明哪些数据采用了默认基准。",
    "production_sequence": "生产顺序号。",
    "assembly_time_days": "部装装配时长（天）；用于部装组在零件排产中的倒排窗口。",
    "parent_material_no": "父级物料号。",
    "part_name": "零件名称。",
    "part_material_no": "零件物料号。",
    "part_raw_material_desc": "零件原材料描述。",
    "part_cycle_days": "单个零件周期（天）；表示该零件自身匹配到的周期基准。",
    "part_cycle_is_default": "零件周期是否采用默认基准。",
    "part_cycle_match_rule": "零件周期匹配规则。",
    "key_part_name": "关键零件名称。",
    "key_part_material_no": "关键零件物料号。",
    "key_part_raw_material_desc": "关键零件原材料描述。",
    "key_part_cycle_days": "关键零件周期（天）；当前口径作为所在部装组倒排开工时间的锚点周期。",
    "is_key_part": "是否关键零件。",
    "bom_path": "BOM 层级路径文本。",
    "bom_path_key": "BOM 层级路径唯一键。",
    "node_level": "BOM 节点层级。",
    "parent_name": "父级节点名称。",
    "issue_type": "异常类型。",
    "issue_level": "异常等级。",
    "source_system": "来源系统。",
    "biz_key": "业务主键。",
    "issue_title": "异常标题。",
    "issue_detail": "异常详情。",
    "created_at": "创建时间。",
    "machine_schedule": "整机排产详情。",
    "part_schedules": "零件排产明细列表。",
    "issues": "关联异常列表。",
    "key": "统计项标识。",
    "count": "统计数量。",
    "total_orders": "订单总数。",
    "scheduled_orders": "已排产订单数。",
    "unscheduled_orders": "未排产订单数。",
    "abnormal_orders": "异常订单数。",
    "status_counts": "按状态聚合的统计结果。",
    "planned_end_month_counts": "按计划完工月份聚合的统计结果。",
    "warning_orders": "预警订单列表。",
    "total_parts": "零件总数。",
    "abnormal_parts": "异常零件数。",
    "warning_counts": "预警统计结果。",
    "top_assemblies": "高频部装统计列表。",
    "delivery_count": "交付相关订单数。",
    "unscheduled_count": "未排产数量。",
    "abnormal_count": "异常数量。",
    "machine_summary": "整机排产概览统计。",
    "part_summary": "零件排产概览统计。",
    "today_summary": "今日时间窗口概览。",
    "week_summary": "本周时间窗口概览。",
    "month_summary": "本月时间窗口概览。",
    "delivery_risk_orders": "交付风险订单列表。",
    "calendar_date": "日历日期。",
    "delivery_order_count": "当天交付订单数。",
    "delivery_quantity_sum": "当天交付数量汇总。",
    "trigger_order_count": "当天触发订单数。",
    "trigger_quantity_sum": "当天触发数量汇总。",
    "planned_start_order_count": "当天计划开工订单数。",
    "planned_start_quantity_sum": "当天计划开工数量汇总。",
    "summary": "日期汇总信息。",
    "delivery_orders": "当天交付订单列表。",
    "trigger_orders": "当天触发订单列表。",
    "planned_start_orders": "当天计划开工订单列表。",
}


OPENAPI_PARAMETER_SECTION_TITLES = {
    "path": "路径参数",
    "query": "查询参数",
    "header": "请求头",
    "cookie": "Cookie 参数",
}


OPENAPI_RESPONSE_EXAMPLES = {
    ("post", "/api/auth/login", "200"): {
        "code": 0,
        "message": "success",
        "data": {
            "authenticated": True,
            "user": {
                "id": 1,
                "username": "admin",
                "display_name": "系统管理员",
                "is_active": True,
                "last_login_at": "2026-03-23T10:00:00Z",
                "created_at": "2026-03-23T09:00:00Z",
                "updated_at": "2026-03-23T09:00:00Z",
                "roles": [{"code": "admin", "name": "管理员"}],
            },
            "expires_at": "2026-03-23T18:00:00Z",
        },
    },
    ("get", "/api/auth/session", "200"): {
        "code": 0,
        "message": "success",
        "data": {
            "authenticated": True,
            "user": {
                "id": 1,
                "username": "admin",
                "display_name": "系统管理员",
                "is_active": True,
                "last_login_at": "2026-03-23T10:00:00Z",
                "created_at": "2026-03-23T09:00:00Z",
                "updated_at": "2026-03-23T09:00:00Z",
                "roles": [{"code": "admin", "name": "管理员"}],
            },
            "expires_at": "2026-03-23T18:00:00Z",
        },
    },
    ("post", "/api/admin/schedule/run", "200"): {
        "code": 0,
        "message": "success",
        "data": {
            "run_batch_no": "SCH20260323153000",
            "total": 3,
            "success_count": 3,
            "fail_count": 0,
            "message": None,
        },
    },
    ("post", "/api/admin/issues/{issue_id}/resolve", "200"): {
        "code": 0,
        "message": "success",
        "data": {
            "id": 101,
            "status": "resolved",
        },
    },
    ("get", "/api/schedules", "200"): {
        "code": 0,
        "message": "success",
        "data": {
            "total": 1,
            "page_no": 1,
            "page_size": 20,
            "items": [
                {
                    "order_line_id": 101,
                    "contract_no": "HT20260323001",
                    "customer_name": "江苏某客户",
                    "product_series": "X7",
                    "product_model": "X7-500",
                    "order_no": "SO20260323001",
                    "quantity": 1,
                    "confirmed_delivery_date": "2026-03-30T00:00:00",
                    "planned_start_date": "2026-03-24T00:00:00",
                    "planned_end_date": "2026-03-28T00:00:00",
                    "warning_level": "normal",
                    "schedule_status": "scheduled",
                }
            ],
        },
    },
}


OPENAPI_VALIDATION_ERROR_EXAMPLE = {
    "detail": [
        {
            "loc": ["body", "order_line_ids"],
            "msg": "Field required",
            "type": "missing",
        }
    ]
}


OPENAPI_AUTH_ERROR_EXAMPLE = {
    "detail": "User session is invalid or expired."
}


OPENAPI_FORBIDDEN_ERROR_EXAMPLE = {
    "detail": "Current user does not have the required permission."
}


def _apply_openapi_descriptions(schema: dict) -> None:
    components = schema.get("components", {}).get("schemas", {})
    security_schemes = schema.setdefault("components", {}).setdefault("securitySchemes", {})

    if AUTH_SESSION_SECURITY_SCHEME_NAME in security_schemes:
        security_schemes[AUTH_SESSION_SECURITY_SCHEME_NAME]["description"] = (
            f"用户登录成功后写入浏览器的会话 Cookie。"
            f"调用受保护接口时请携带 `{settings.user_session_cookie_name}`。"
        )

    for schema_name, schema_item in components.items():
        schema_description = OPENAPI_SCHEMA_DESCRIPTIONS.get(schema_name)
        if schema_description and not schema_item.get("description"):
            schema_item["description"] = schema_description

        for field_name, field_schema in schema_item.get("properties", {}).items():
            if field_schema.get("description"):
                continue
            schema_level_description = OPENAPI_SCHEMA_FIELD_DESCRIPTIONS.get(schema_name, {}).get(field_name)
            if schema_level_description:
                field_schema["description"] = schema_level_description
                continue
            description = OPENAPI_FIELD_DESCRIPTIONS.get(field_name)
            if description:
                field_schema["description"] = description

    for path, methods in schema.get("paths", {}).items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue

            for parameter in operation.get("parameters", []):
                parameter_name = parameter.get("name")
                if parameter_name == "user_session":
                    parameter.setdefault("example", "浏览器登录后自动携带")
                if parameter.get("description"):
                    continue
                description = OPENAPI_PARAMETER_DESCRIPTIONS.get(parameter_name)
                if description:
                    parameter["description"] = description

            request_body = operation.get("requestBody")
            if request_body and not request_body.get("description"):
                for media in request_body.get("content", {}).values():
                    ref = media.get("schema", {}).get("$ref")
                    if not ref:
                        continue
                    schema_name = ref.rsplit("/", 1)[-1]
                    schema_description = components.get(schema_name, {}).get("description")
                    if schema_description:
                        request_body["description"] = f"{schema_description.rstrip('。')}。各字段中文说明见下方 Schema 区域。"
                        break

            _apply_response_descriptions_and_examples(
                path=path,
                method=method,
                operation=operation,
                components=components,
            )

            operation["description"] = _build_operation_io_sections(
                operation=operation,
                components=components,
                security_schemes=security_schemes,
            )


def _apply_response_descriptions_and_examples(
    *,
    path: str,
    method: str,
    operation: dict,
    components: dict,
) -> None:
    responses = operation.get("responses", {})
    is_export_operation = "导出" in (operation.get("tags") or [])
    is_permission_protected_operation = bool(operation.get("security"))

    if operation.get("security") and "401" not in responses:
        responses["401"] = {
            "description": "未登录、会话过期或管理员会话无效。",
            "content": {
                "application/json": {
                    "example": OPENAPI_AUTH_ERROR_EXAMPLE,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "description": "错误详情说明。",
                            }
                        },
                    },
                }
            },
        }
    if is_permission_protected_operation and "403" not in responses:
        responses["403"] = {
            "description": "已登录，但当前用户不具备接口所需权限点。",
            "content": {
                "application/json": {
                    "example": OPENAPI_FORBIDDEN_ERROR_EXAMPLE,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "description": "错误详情说明。",
                            }
                        },
                    },
                }
            },
        }

    for status_code, response in responses.items():
        if not isinstance(response, dict):
            continue

        if status_code == "401":
            response.setdefault("description", "未登录、会话过期或管理员会话无效。")
            for media in response.get("content", {}).values():
                media.setdefault("example", OPENAPI_AUTH_ERROR_EXAMPLE)
            continue

        if status_code == "403":
            response.setdefault("description", "已登录，但当前用户不具备接口所需权限点。")
            for media in response.get("content", {}).values():
                media.setdefault("example", OPENAPI_FORBIDDEN_ERROR_EXAMPLE)
            continue

        if is_export_operation and status_code == "200":
            response["description"] = "导出成功时直接返回文件流，不走 JSON 包装。"
            response["content"] = {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                    "schema": {"type": "string", "format": "binary"}
                },
                "text/csv": {
                    "schema": {"type": "string", "format": "binary"}
                },
            }
            continue

        if status_code == "422":
            response["description"] = "请求参数或请求体校验失败。"
            for media in response.get("content", {}).values():
                media.setdefault("example", OPENAPI_VALIDATION_ERROR_EXAMPLE)
            continue

        if status_code != "200":
            continue

        json_content = response.get("content", {}).get("application/json")
        if not json_content:
            continue

        schema_ref = json_content.get("schema", {}).get("$ref")
        response_schema_name = schema_ref.rsplit("/", 1)[-1] if schema_ref else None
        inner_schema_name = _extract_api_response_inner_schema_name(
            response_schema_name=response_schema_name,
            components=components,
        )

        if response_schema_name:
            if inner_schema_name:
                response["description"] = (
                    f"标准成功响应，外层为 `{response_schema_name}`，其中 `data` 字段为 `{inner_schema_name}`。"
                )
            else:
                response["description"] = f"标准成功响应，返回结构为 `{response_schema_name}`。"

        example = OPENAPI_RESPONSE_EXAMPLES.get((method.lower(), path, status_code))
        if example is not None:
            json_content.setdefault("example", example)


def _extract_api_response_inner_schema_name(*, response_schema_name: str | None, components: dict) -> str | None:
    if not response_schema_name or not response_schema_name.startswith("ApiResponse_"):
        return None
    schema_item = components.get(response_schema_name, {})
    data_schema = schema_item.get("properties", {}).get("data", {})
    for candidate in data_schema.get("anyOf", []):
        ref = candidate.get("$ref")
        if ref:
            return ref.rsplit("/", 1)[-1]
    return None


def _build_operation_io_sections(
    *,
    operation: dict,
    components: dict,
    security_schemes: dict,
) -> str:
    base_description = (operation.get("description") or "").strip()
    if not base_description:
        base_description = f"{operation.get('summary', '该接口')}。"
    grouped_parameters: dict[str, list[str]] = defaultdict(list)

    for parameter in operation.get("parameters", []):
        parameter_name = parameter.get("name", "unknown")
        location = parameter.get("in", "query")
        required = "必填" if parameter.get("required") else "可选"
        description = parameter.get("description") or "请参考接口字段定义。"
        grouped_parameters[location].append(f"- `{parameter_name}`（{required}）：{description}")

    sections: list[str] = []
    security_lines: list[str] = []
    for security_item in operation.get("security") or []:
        for scheme_name in security_item.keys():
            scheme = security_schemes.get(scheme_name, {})
            if not scheme:
                continue
            scheme_type = scheme.get("type")
            scheme_in = scheme.get("in")
            scheme_target = scheme.get("name", scheme_name)
            scheme_description = scheme.get("description") or "请先完成认证后再调用。"
            if scheme_type == "apiKey" and scheme_in == "cookie":
                security_lines.append(f"- Cookie `{scheme_target}`：{scheme_description}")
            elif scheme_type == "apiKey" and scheme_in == "header":
                security_lines.append(f"- 请求头 `{scheme_target}`：{scheme_description}")
            else:
                security_lines.append(f"- `{scheme_name}`：{scheme_description}")
    if security_lines:
        sections.append("#### 认证信息\n" + "\n".join(security_lines))

    for location in ("path", "query", "header", "cookie"):
        lines = grouped_parameters.get(location)
        if lines:
            title = OPENAPI_PARAMETER_SECTION_TITLES[location]
            sections.append(f"#### {title}\n" + "\n".join(lines))

    request_body = operation.get("requestBody")
    if request_body:
        request_body_lines: list[str] = []
        request_body_description = request_body.get("description")
        if request_body_description:
            request_body_lines.append(f"- 结构说明：{request_body_description}")
        for media_type, media in request_body.get("content", {}).items():
            schema_ref = media.get("schema", {}).get("$ref")
            if not schema_ref:
                request_body_lines.append(f"- 媒体类型 `{media_type}`：请参考下方 Schema 区域。")
                continue
            schema_name = schema_ref.rsplit("/", 1)[-1]
            schema_description = components.get(schema_name, {}).get("description") or "请参考下方 Schema 区域。"
            request_body_lines.append(f"- `{media_type}`：`{schema_name}`，{schema_description}")
        if request_body_lines:
            sections.append("#### 请求体\n" + "\n".join(request_body_lines))

    response_lines: list[str] = []
    for status_code, response in operation.get("responses", {}).items():
        if not isinstance(response, dict):
            continue
        response_description = response.get("description") or "请参考返回体定义。"
        response_lines.append(f"- `{status_code}`：{response_description}")
    if response_lines:
        sections.append("#### 响应结构\n" + "\n".join(response_lines))

    if not sections:
        return base_description

    input_summary = "### 接口结构\n" + "\n\n".join(sections)
    return f"{base_description}\n\n{input_summary}".strip()


def build_custom_openapi(app: FastAPI):
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            summary=app.summary,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        _apply_openapi_descriptions(openapi_schema)
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return custom_openapi
