from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.routing import APIRoute
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.exceptions import BizException, ErrorCode
from app.common.response import ApiResponse
from app.database import get_session
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_account import UserAccount
from app.models.user_role import UserRole
from app.repository.permission_repo import PermissionRepo
from app.repository.role_repo import RoleRepo
from app.repository.user_account_repo import UserAccountRepo
from app.repository.user_session_repo import UserSessionRepo
from app.schemas.auth_schemas import (
    AdminPermissionLinkageResponse,
    AdminPermissionListResponse,
    AdminPermissionMatrixResponse,
    AdminRoleDetailResponse,
    AdminRoleItemResponse,
    AdminRoleListResponse,
    AdminRolePermissionListResponse,
    AdminUserDetailResponse,
    AdminUserItemResponse,
    AdminUserListPageResponse,
    RoleCreateRequest,
    RolePermissionUpdateRequest,
    RoleStatusUpdateRequest,
    RoleUpdateRequest,
    UserCreateRequest,
    UserPasswordResetRequest,
    UserRoleUpdateRequest,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)
from app.services.user_auth_service import (
    ensure_permissions_exist,
    ensure_roles_exist,
    hash_password,
    normalize_role_code,
    serialize_permission_payload,
    serialize_role_payload,
    serialize_user_payload,
    user_has_role,
)

router = APIRouter(prefix="/api/admin", tags=["用户管理"])

require_user_view_permission = require_permission("user.view")
require_user_manage_permission = require_permission("user.manage")
require_role_view_permission = require_permission("role.view")
require_role_manage_permission = require_permission("role.manage")
require_permission_view_permission = require_permission("permission.view")


def _serialize_admin_user_item(user: UserAccount) -> dict[str, object]:
    payload = serialize_user_payload(user)
    payload["session_source"] = None
    return payload


def _serialize_role_detail(
    role: Role, *, assigned_user_count: int = 0, permission_count: int | None = None
) -> dict[str, object]:
    payload = serialize_role_payload(role, assigned_user_count=assigned_user_count, permission_count=permission_count)
    payload["permissions"] = [
        serialize_permission_payload(link.permission)
        for link in role.permission_links
        if getattr(link, "permission", None) is not None
    ]
    return payload


def _build_permission_route_linkage(app) -> dict[str, list[dict[str, object]]]:
    linkage: dict[str, list[dict[str, object]]] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        permission_codes: set[str] = set()
        for dependency in route.dependant.dependencies:
            permission_codes.update(getattr(dependency.call, "__required_permission_codes__", ()))
        if not permission_codes:
            continue

        route_payload = {
            "path": route.path,
            "methods": sorted(method for method in (route.methods or []) if method not in {"HEAD", "OPTIONS"}),
            "tags": list(route.tags or []),
            "summary": route.summary,
            "description": route.description,
        }
        for permission_code in sorted(permission_codes):
            linkage.setdefault(permission_code, []).append(route_payload)

    for items in linkage.values():
        items.sort(key=lambda item: (item["path"], ",".join(item["methods"])))
    return linkage


async def _get_user_or_raise(repo: UserAccountRepo, user_id: int) -> UserAccount:
    user = await repo.get_with_roles(user_id)
    if user is None:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "用户不存在")
    return user


async def _get_role_or_raise(repo: RoleRepo, role_id: int) -> Role:
    role = await repo.get_with_permissions(role_id)
    if role is None:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "角色不存在")
    return role


@router.get(
    "/users",
    summary="获取系统用户分页列表",
    description="按关键字、角色和启用状态分页查询系统用户列表。",
    response_model=ApiResponse[AdminUserListPageResponse],
)
async def list_users(
    keyword: str | None = Query(default=None, description="按登录账号或显示名称模糊搜索"),
    role_code: str | None = Query(default=None, description="按角色编码筛选用户"),
    is_active: bool | None = Query(default=None, description="按用户启用状态筛选"),
    page_no: int = Query(default=1, ge=1, description="分页页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，最大 100"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_user_view_permission),
) -> ApiResponse[Any]:

    items, total = await UserAccountRepo(session).list_with_roles(
        keyword=keyword,
        role_code=normalize_role_code(role_code) if role_code else None,
        is_active=is_active,
        page_no=page_no,
        page_size=page_size,
    )
    return ApiResponse.ok(
        data={
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
            "items": [_serialize_admin_user_item(user) for user in items],
        }
    )


@router.get(
    "/users/{user_id}",
    summary="获取用户详情",
    description="返回指定用户的账号、状态、角色和时间字段详情。",
    response_model=ApiResponse[AdminUserDetailResponse],
)
async def get_user(
    user_id: int = Path(description="用户 ID"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_user_view_permission),
) -> ApiResponse[Any]:
    user = await _get_user_or_raise(UserAccountRepo(session), user_id)
    return ApiResponse.ok(data=_serialize_admin_user_item(user))


@router.post(
    "/users",
    summary="新建系统用户",
    description="创建账号密码用户，并分配一个或多个角色。",
    response_model=ApiResponse[AdminUserItemResponse],
)
async def create_user(
    payload: UserCreateRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_user_manage_permission),
) -> ApiResponse[Any]:

    repo = UserAccountRepo(session)

    username = payload.username.strip()
    display_name = payload.display_name.strip()
    password = payload.password
    role_codes = [code.strip() for code in payload.role_codes if code and code.strip()]

    if not username:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "账号不能为空")
    if not display_name:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "显示名称不能为空")
    if not password:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "密码不能为空")
    if await repo.is_username_taken(username):
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "账号已存在")

    roles = await ensure_roles_exist(session, role_codes)
    user = UserAccount(
        username=username,
        display_name=display_name,
        password_hash=hash_password(password),
        is_active=payload.is_active,
    )
    session.add(user)
    await session.flush()
    session.add_all([UserRole(user_id=user.id, role_id=role.id) for role in roles])
    await session.commit()

    created_user = await repo.get_with_roles(user.id)
    return ApiResponse.ok(data=_serialize_admin_user_item(created_user or user))


@router.put(
    "/users/{user_id}",
    summary="编辑用户基础资料",
    description="编辑用户登录账号与显示名称，不影响当前用户已绑定角色。",
    response_model=ApiResponse[AdminUserItemResponse],
)
async def update_user(
    payload: UserUpdateRequest,
    user_id: int = Path(description="用户 ID"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_user_manage_permission),
) -> ApiResponse[Any]:
    repo = UserAccountRepo(session)
    user = await _get_user_or_raise(repo, user_id)

    username = payload.username.strip()
    display_name = payload.display_name.strip()
    if not username:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "账号不能为空")
    if not display_name:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "显示名称不能为空")
    if await repo.is_username_taken(username, exclude_user_id=user.id):
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "账号已存在")

    user.username = username
    user.display_name = display_name
    await session.commit()
    refreshed_user = await repo.get_with_roles(user.id) or user
    return ApiResponse.ok(data=_serialize_admin_user_item(refreshed_user))


@router.patch(
    "/users/{user_id}/status",
    summary="启用或停用系统用户",
    description="更新用户启用状态；停用用户时会立即撤销该用户全部活跃会话，避免旧会话继续访问系统。",
    response_model=ApiResponse[AdminUserItemResponse],
)
async def update_user_status(
    payload: UserStatusUpdateRequest,
    user_id: int = Path(description="用户 ID"),
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUserIdentity = Depends(require_user_manage_permission),
) -> ApiResponse[Any]:
    repo = UserAccountRepo(session)
    user = await _get_user_or_raise(repo, user_id)
    if current_user.user_id == user.id and not payload.is_active:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "不能停用当前登录用户")

    user.is_active = payload.is_active
    if not payload.is_active:
        await UserSessionRepo(session).revoke_active_sessions_for_user(user.id)
    await session.commit()
    refreshed_user = await repo.get_with_roles(user.id) or user
    return ApiResponse.ok(data=_serialize_admin_user_item(refreshed_user))


@router.post(
    "/users/{user_id}/reset-password",
    summary="重置用户密码",
    description="重置指定用户密码；密码更新后会立即撤销该用户全部活跃会话，要求用户重新登录。",
    response_model=ApiResponse[AdminUserItemResponse],
)
async def reset_user_password(
    payload: UserPasswordResetRequest,
    user_id: int = Path(description="用户 ID"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_user_manage_permission),
) -> ApiResponse[Any]:
    repo = UserAccountRepo(session)
    user = await _get_user_or_raise(repo, user_id)

    new_password = payload.new_password

    user.password_hash = hash_password(new_password)
    await UserSessionRepo(session).revoke_active_sessions_for_user(user.id)
    await session.commit()
    refreshed_user = await repo.get_with_roles(user.id) or user
    return ApiResponse.ok(data=_serialize_admin_user_item(refreshed_user))


@router.put(
    "/users/{user_id}/roles",
    summary="更新用户角色",
    description="更新指定用户角色列表，至少保留一个角色，并阻止当前登录管理员移除自己的管理员角色。",
    response_model=ApiResponse[AdminUserItemResponse],
)
async def update_user_roles(
    payload: UserRoleUpdateRequest,
    user_id: int = Path(description="用户 ID"),
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUserIdentity = Depends(require_user_manage_permission),
) -> ApiResponse[Any]:
    repo = UserAccountRepo(session)
    user = await _get_user_or_raise(repo, user_id)

    role_codes = [code.strip() for code in payload.role_codes if code and code.strip()]
    normalized_role_codes = {code.strip().lower() for code in role_codes}
    if current_user.user_id == user.id and user_has_role(user, "admin") and "admin" not in normalized_role_codes:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "不能移除当前登录用户的管理员角色")

    roles = await ensure_roles_exist(session, role_codes)
    await session.execute(delete(UserRole).where(UserRole.user_id == user.id))
    await session.flush()
    session.add_all([UserRole(user_id=user.id, role_id=role.id) for role in roles])
    await session.commit()

    refreshed_user = await repo.get_with_roles(user.id) or user
    return ApiResponse.ok(data=_serialize_admin_user_item(refreshed_user))


@router.get(
    "/roles",
    summary="获取角色列表",
    description="返回角色列表及绑定用户数、权限数。",
    response_model=ApiResponse[AdminRoleListResponse],
)
async def list_roles(
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_role_view_permission),
) -> ApiResponse[Any]:

    repo = RoleRepo(session)
    roles = await repo.list_with_permissions(include_inactive=True)
    role_ids = [role.id for role in roles]
    user_counts = await repo.count_assigned_users(role_ids)
    permission_counts = await repo.count_permissions(role_ids)
    return ApiResponse.ok(
        data={
            "items": [
                serialize_role_payload(
                    role,
                    assigned_user_count=user_counts.get(role.id, 0),
                    permission_count=permission_counts.get(role.id, 0),
                )
                for role in roles
            ]
        }
    )


@router.get(
    "/roles/{role_id}",
    summary="获取角色详情",
    description="返回指定角色的基本信息及当前绑定权限目录。",
    response_model=ApiResponse[AdminRoleDetailResponse],
)
async def get_role(
    role_id: int = Path(description="角色 ID"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_role_view_permission),
) -> ApiResponse[Any]:
    repo = RoleRepo(session)
    role = await _get_role_or_raise(repo, role_id)
    assigned_user_count = (await repo.count_assigned_users([role.id])).get(role.id, 0)
    permission_count = (await repo.count_permissions([role.id])).get(role.id, 0)
    return ApiResponse.ok(
        data=_serialize_role_detail(
            role,
            assigned_user_count=assigned_user_count,
            permission_count=permission_count,
        )
    )


@router.post(
    "/roles",
    summary="新建角色",
    description="创建新的可分配角色，角色编码用于系统内部标识，角色名称使用中文展示。",
    response_model=ApiResponse[AdminRoleItemResponse],
)
async def create_role(
    payload: RoleCreateRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_role_manage_permission),
) -> ApiResponse[Any]:

    repo = RoleRepo(session)
    code = normalize_role_code(payload.code)
    name = payload.name.strip()
    description = payload.description.strip() if payload.description else None

    if not name:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "角色名称不能为空")
    if await repo.find_by_code(code):
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "角色编码已存在")

    role = Role(
        code=code,
        name=name,
        description=description,
        is_active=payload.is_active,
        is_system=False,
    )
    session.add(role)
    await session.commit()
    created_role = await repo.get_with_permissions(role.id) or role
    return ApiResponse.ok(data=serialize_role_payload(created_role, assigned_user_count=0, permission_count=0))


@router.put(
    "/roles/{role_id}",
    summary="编辑角色信息",
    description="编辑角色中文名称与说明，不修改角色编码。",
    response_model=ApiResponse[AdminRoleItemResponse],
)
async def update_role(
    payload: RoleUpdateRequest,
    role_id: int = Path(description="角色 ID"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_role_manage_permission),
) -> ApiResponse[Any]:
    repo = RoleRepo(session)
    role = await _get_role_or_raise(repo, role_id)
    name = payload.name.strip()
    if not name:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "角色名称不能为空")

    role.name = name
    role.description = payload.description.strip() if payload.description else None
    await session.commit()
    refreshed_role = await repo.get_with_permissions(role.id) or role
    assigned_user_count = (await repo.count_assigned_users([role.id])).get(role.id, 0)
    permission_count = (await repo.count_permissions([role.id])).get(role.id, 0)
    return ApiResponse.ok(
        data=serialize_role_payload(
            refreshed_role,
            assigned_user_count=assigned_user_count,
            permission_count=permission_count,
        )
    )


@router.patch(
    "/roles/{role_id}/status",
    summary="启用或停用角色",
    description="更新角色启用状态，系统内置角色不允许停用。",
    response_model=ApiResponse[AdminRoleItemResponse],
)
async def update_role_status(
    payload: RoleStatusUpdateRequest,
    role_id: int = Path(description="角色 ID"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_role_manage_permission),
) -> ApiResponse[Any]:
    repo = RoleRepo(session)
    role = await _get_role_or_raise(repo, role_id)
    if role.is_system and not payload.is_active:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "系统内置角色不允许停用")

    role.is_active = payload.is_active
    await session.commit()
    refreshed_role = await repo.get_with_permissions(role.id) or role
    assigned_user_count = (await repo.count_assigned_users([role.id])).get(role.id, 0)
    permission_count = (await repo.count_permissions([role.id])).get(role.id, 0)
    return ApiResponse.ok(
        data=serialize_role_payload(
            refreshed_role,
            assigned_user_count=assigned_user_count,
            permission_count=permission_count,
        )
    )


@router.put(
    "/roles/{role_id}/permissions",
    summary="更新角色权限列表",
    description="更新指定自定义角色的权限点列表；系统内置角色权限不允许通过该接口修改。",
    response_model=ApiResponse[AdminRoleDetailResponse],
)
async def update_role_permissions(
    payload: RolePermissionUpdateRequest,
    role_id: int = Path(description="角色 ID"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_role_manage_permission),
) -> ApiResponse[Any]:
    repo = RoleRepo(session)
    role = await _get_role_or_raise(repo, role_id)
    if role.is_system:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "系统内置角色权限不允许修改")

    permissions = await ensure_permissions_exist(session, payload.permission_codes)
    await session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    await session.flush()
    if permissions:
        session.add_all([RolePermission(role_id=role.id, permission_id=permission.id) for permission in permissions])
    await session.commit()

    refreshed_role = await repo.get_with_permissions(role.id) or role
    assigned_user_count = (await repo.count_assigned_users([role.id])).get(role.id, 0)
    permission_count = (await repo.count_permissions([role.id])).get(role.id, 0)
    return ApiResponse.ok(
        data=_serialize_role_detail(
            refreshed_role,
            assigned_user_count=assigned_user_count,
            permission_count=permission_count,
        )
    )


@router.delete(
    "/roles/{role_id}",
    summary="删除角色",
    description="删除指定角色；系统内置角色或仍有用户绑定的角色不允许删除。",
    response_model=ApiResponse[None],
)
async def delete_role(
    role_id: int = Path(description="角色 ID"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_role_manage_permission),
) -> ApiResponse[Any]:
    repo = RoleRepo(session)
    role = await _get_role_or_raise(repo, role_id)
    if role.is_system:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "系统内置角色不允许删除")

    assigned_user_count = (await repo.count_assigned_users([role.id])).get(role.id, 0)
    if assigned_user_count > 0:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "当前角色仍有用户绑定，无法删除")

    await session.delete(role)
    await session.commit()
    return ApiResponse.ok(data=None)


@router.get(
    "/permissions",
    summary="获取权限目录骨架",
    description="返回系统内置权限目录，用于用户管理页中的权限占位展示。",
    response_model=ApiResponse[AdminPermissionListResponse],
)
async def list_permissions(
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_permission_view_permission),
) -> ApiResponse[Any]:

    permissions = await PermissionRepo(session).list_all_ordered()
    return ApiResponse.ok(data={"items": [serialize_permission_payload(permission) for permission in permissions]})


@router.get(
    "/permission-linkage",
    summary="获取权限点与后端接口联动清单",
    description="返回每个权限点关联的受保护后端接口列表，用于前端权限矩阵、菜单显隐和按钮级联动说明。",
    response_model=ApiResponse[AdminPermissionLinkageResponse],
)
async def get_permission_linkage(
    request: Request,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_permission_view_permission),
) -> ApiResponse[Any]:

    permissions = await PermissionRepo(session).list_all_ordered()
    route_linkage = _build_permission_route_linkage(request.app)
    return ApiResponse.ok(
        data={
            "items": [
                {
                    **serialize_permission_payload(permission),
                    "linked_routes": list(route_linkage.get(permission.code, [])),
                }
                for permission in permissions
            ]
        }
    )


@router.get(
    "/permission-matrix",
    summary="获取角色权限矩阵",
    description="返回角色列表与权限目录的矩阵视图，用于前端权限矩阵展示和按钮级联动说明。",
    response_model=ApiResponse[AdminPermissionMatrixResponse],
)
async def get_permission_matrix(
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_role_view_permission),
    __: CurrentUserIdentity = Depends(require_permission_view_permission),
) -> ApiResponse[Any]:

    role_repo = RoleRepo(session)
    permission_repo = PermissionRepo(session)

    roles = await role_repo.list_with_permissions(include_inactive=True)
    permissions = await permission_repo.list_all_ordered()
    role_ids = [role.id for role in roles]
    user_counts = await role_repo.count_assigned_users(role_ids)
    permission_counts = await role_repo.count_permissions(role_ids)
    role_permission_codes = {
        role.id: {
            link.permission.code for link in role.permission_links if getattr(link, "permission", None) is not None
        }
        for role in roles
    }

    return ApiResponse.ok(
        data={
            "roles": [
                {
                    "id": role.id,
                    "code": role.code,
                    "name": role.name,
                    "is_active": role.is_active,
                    "is_system": role.is_system,
                    "assigned_user_count": user_counts.get(role.id, 0),
                    "permission_count": permission_counts.get(role.id, 0),
                }
                for role in roles
            ],
            "permissions": [
                {
                    **serialize_permission_payload(permission),
                    "role_bindings": [
                        {
                            "role_id": role.id,
                            "role_code": role.code,
                            "assigned": permission.code in role_permission_codes.get(role.id, set()),
                        }
                        for role in roles
                    ],
                }
                for permission in permissions
            ],
        }
    )


@router.get(
    "/roles/{role_id}/permissions",
    summary="获取角色权限占位详情",
    description="返回指定角色当前绑定的权限目录，用于后续 RBAC 扩展。",
    response_model=ApiResponse[AdminRolePermissionListResponse],
)
async def get_role_permissions(
    role_id: int = Path(description="角色 ID"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_permission_view_permission),
) -> ApiResponse[Any]:
    role = await _get_role_or_raise(RoleRepo(session), role_id)
    return ApiResponse.ok(
        data={
            "role_id": role.id,
            "role_code": role.code,
            "role_name": role.name,
            "items": [
                serialize_permission_payload(link.permission)
                for link in role.permission_links
                if getattr(link, "permission", None) is not None
            ],
        }
    )
