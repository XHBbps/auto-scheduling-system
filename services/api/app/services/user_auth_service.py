from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
import secrets

from app.common.exceptions import BizException, ErrorCode
from app.config import settings
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_account import UserAccount
from app.models.user_role import UserRole
from app.repository.permission_repo import PermissionRepo
from app.repository.role_repo import RoleRepo
from app.repository.user_account_repo import UserAccountRepo

ADMIN_ROLE_CODE = "admin"
ADMIN_ROLE_NAME = "管理员"
ADMIN_ROLE_DESCRIPTION = "系统内置管理员角色，默认拥有全部系统管理权限。"
ROLE_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{1,49}$")


@dataclass(slots=True)
class UserRoleView:
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class PermissionSeed:
    code: str
    name: str
    module_name: str
    description: str
    sort_order: int


SYSTEM_PERMISSION_SEEDS: tuple[PermissionSeed, ...] = (
    PermissionSeed("user.view", "查看用户", "系统管理", "查看用户列表、详情与状态信息。", 10),
    PermissionSeed("user.manage", "维护用户", "系统管理", "创建用户、编辑用户、重置密码与调整角色。", 20),
    PermissionSeed("role.view", "查看角色", "系统管理", "查看角色列表、角色详情与角色绑定关系。", 30),
    PermissionSeed("role.manage", "维护角色", "系统管理", "创建角色、编辑角色、停用角色与删除角色。", 40),
    PermissionSeed("permission.view", "查看权限骨架", "系统管理", "查看系统内置权限目录与角色权限占位信息。", 50),
    PermissionSeed("sync.manage", "执行数据同步", "同步配置", "触发数据同步并查看同步链路信息。", 60),
    PermissionSeed("sync.log.view", "查看同步日志", "同步配置", "查看同步日志、调度状态和观测摘要。", 70),
    PermissionSeed("schedule.view", "查看排产数据", "排产控制", "查看排产总览、整机排产列表、零件排产列表与排产详情。", 80),
    PermissionSeed("schedule.manage", "执行排产任务", "排产控制", "触发一键排产、单订单排产与快照刷新。", 90),
    PermissionSeed("issue.view", "查看异常", "排产控制", "查看排产异常列表、异常筛选和关联订单快照信息。", 100),
    PermissionSeed("issue.manage", "处理异常", "排产控制", "处理排产异常记录，如解决或忽略异常。", 110),
    PermissionSeed("settings.manage", "维护基础参数", "基础参数", "维护装配时长、整机周期、零件周期和工作日历等基础参数。", 120),
    PermissionSeed("data_source.view", "查看外源数据", "数据查看", "查看销售计划、BOM、生产订单和整机周期历史等外源数据。", 130),
    PermissionSeed("export.view", "导出排产结果", "数据查看", "导出整机排产和零件排产结果文件。", 140),
)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${key.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt_hex, key_hex = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "scrypt":
        return False
    salt = bytes.fromhex(salt_hex)
    expected_key = bytes.fromhex(key_hex)
    actual_key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return secrets.compare_digest(actual_key, expected_key)


def build_user_role_views(user: UserAccount) -> list[UserRoleView]:
    role_views = [
        UserRoleView(code=link.role.code, name=link.role.name)
        for link in user.role_links
        if getattr(link, "role", None) is not None and getattr(link.role, "is_active", True)
    ]
    return sorted(role_views, key=lambda item: item.code)


def build_user_permission_codes(user: UserAccount) -> list[str]:
    permission_codes = {
        link.permission.code
        for role_link in user.role_links
        if getattr(role_link, "role", None) is not None and getattr(role_link.role, "is_active", True)
        for link in getattr(role_link.role, "permission_links", [])
        if getattr(link, "permission", None) is not None and getattr(link.permission, "is_active", True)
    }
    return sorted(permission_codes)


def serialize_user_payload(user: UserAccount) -> dict[str, object]:
    role_views = build_user_role_views(user)
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat().replace("+00:00", "Z") if user.last_login_at else None,
        "created_at": user.created_at.isoformat().replace("+00:00", "Z") if getattr(user, "created_at", None) else None,
        "updated_at": user.updated_at.isoformat().replace("+00:00", "Z") if getattr(user, "updated_at", None) else None,
        "roles": [{"code": role.code, "name": role.name} for role in role_views],
        "permission_codes": build_user_permission_codes(user),
    }


def serialize_role_payload(
    role: Role,
    *,
    assigned_user_count: int = 0,
    permission_count: int | None = None,
) -> dict[str, object]:
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "is_active": role.is_active,
        "is_system": role.is_system,
        "assigned_user_count": assigned_user_count,
        "permission_count": permission_count if permission_count is not None else len(
            [
                link
                for link in getattr(role, "permission_links", [])
                if getattr(link, "permission", None) is not None and getattr(link.permission, "is_active", True)
            ]
        ),
        "created_at": role.created_at.isoformat().replace("+00:00", "Z") if getattr(role, "created_at", None) else None,
        "updated_at": role.updated_at.isoformat().replace("+00:00", "Z") if getattr(role, "updated_at", None) else None,
    }


def serialize_permission_payload(permission: Permission) -> dict[str, object]:
    return {
        "id": permission.id,
        "code": permission.code,
        "name": permission.name,
        "module_name": permission.module_name,
        "description": permission.description,
        "sort_order": permission.sort_order,
        "is_active": permission.is_active,
        "is_system": permission.is_system,
        "created_at": permission.created_at.isoformat().replace("+00:00", "Z") if getattr(permission, "created_at", None) else None,
        "updated_at": permission.updated_at.isoformat().replace("+00:00", "Z") if getattr(permission, "updated_at", None) else None,
    }


def normalize_role_code(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "角色编码不能为空")
    if not ROLE_CODE_PATTERN.match(normalized):
        raise BizException(
            ErrorCode.BIZ_VALIDATION_FAILED,
            "角色编码仅支持小写字母开头，并可包含小写字母、数字、点、下划线与中划线",
        )
    return normalized


def resolve_bootstrap_admin_password() -> str:
    if settings.bootstrap_admin_password.strip():
        return settings.bootstrap_admin_password.strip()
    raise RuntimeError("系统尚未初始化管理员账号，请显式配置 BOOTSTRAP_ADMIN_PASSWORD。")


async def ensure_permissions_seeded(session) -> list[Permission]:
    repo = PermissionRepo(session)
    existing_permissions = await repo.find_by_codes([item.code for item in SYSTEM_PERMISSION_SEEDS])
    permission_map = {permission.code: permission for permission in existing_permissions}

    mutated = False
    for item in SYSTEM_PERMISSION_SEEDS:
        permission = permission_map.get(item.code)
        if permission is None:
            permission = Permission(
                code=item.code,
                name=item.name,
                module_name=item.module_name,
                description=item.description,
                sort_order=item.sort_order,
                is_active=True,
                is_system=True,
            )
            session.add(permission)
            permission_map[item.code] = permission
            mutated = True
            continue

        if permission.name != item.name:
            permission.name = item.name
            mutated = True
        if permission.module_name != item.module_name:
            permission.module_name = item.module_name
            mutated = True
        if permission.description != item.description:
            permission.description = item.description
            mutated = True
        if permission.sort_order != item.sort_order:
            permission.sort_order = item.sort_order
            mutated = True
        if not permission.is_active:
            permission.is_active = True
            mutated = True
        if not permission.is_system:
            permission.is_system = True
            mutated = True

    if mutated:
        await session.flush()

    permissions = list(permission_map.values())
    permissions.sort(key=lambda item: (item.module_name, item.sort_order, item.id or 0))
    return permissions


async def ensure_default_role_permissions(session, role: Role, permissions: list[Permission]) -> None:
    current_permission_ids = {
        link.permission_id
        for link in getattr(role, "permission_links", [])
        if getattr(link, "permission_id", None) is not None
    }
    missing_permission_ids = [permission.id for permission in permissions if permission.id not in current_permission_ids]
    if not missing_permission_ids:
        return
    session.add_all([RolePermission(role_id=role.id, permission_id=permission_id) for permission_id in missing_permission_ids])
    await session.flush()


async def ensure_identity_seeded(session) -> None:
    permissions = await ensure_permissions_seeded(session)
    role_repo = RoleRepo(session)
    admin_role = await role_repo.find_by_code(ADMIN_ROLE_CODE)
    if admin_role is None:
        admin_role = Role(
            code=ADMIN_ROLE_CODE,
            name=ADMIN_ROLE_NAME,
            description=ADMIN_ROLE_DESCRIPTION,
            is_active=True,
            is_system=True,
        )
        session.add(admin_role)
        await session.flush()
    else:
        admin_role.name = ADMIN_ROLE_NAME
        admin_role.description = ADMIN_ROLE_DESCRIPTION
        admin_role.is_active = True
        admin_role.is_system = True

    admin_role_with_permissions = await role_repo.get_with_permissions(admin_role.id)
    if admin_role_with_permissions is None:
        admin_role_with_permissions = admin_role
    await ensure_default_role_permissions(session, admin_role_with_permissions, permissions)

    user_repo = UserAccountRepo(session)
    if await user_repo.exists_any():
        await session.commit()
        return

    username = settings.bootstrap_admin_username.strip() or "admin"
    display_name = settings.bootstrap_admin_display_name.strip() or ADMIN_ROLE_NAME
    bootstrap_password = resolve_bootstrap_admin_password()
    user = UserAccount(
        username=username,
        display_name=display_name,
        password_hash=hash_password(bootstrap_password),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    session.add(UserRole(user_id=user.id, role_id=admin_role.id))
    await session.commit()


async def ensure_permissions_exist(session, permission_codes: list[str], *, active_only: bool = True) -> list[Permission]:
    normalized_codes = sorted({code.strip().lower() for code in permission_codes if code and code.strip()})
    if not normalized_codes:
        return []
    permissions = await PermissionRepo(session).find_by_codes(normalized_codes)
    permission_map = {permission.code: permission for permission in permissions}
    missing = [code for code in normalized_codes if code not in permission_map]
    if missing:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, f"权限不存在：{', ' .join(missing)}")
    if active_only:
        inactive = [code for code, permission in permission_map.items() if not permission.is_active]
        if inactive:
            raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, f"权限已停用，无法分配：{', ' .join(sorted(inactive))}")
    return [permission_map[code] for code in normalized_codes]


async def ensure_roles_exist(session, role_codes: list[str], *, active_only: bool = True) -> list[Role]:
    normalized_codes = sorted({normalize_role_code(code) for code in role_codes if code and code.strip()})
    if not normalized_codes:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, "至少保留一个角色")
    roles = await RoleRepo(session).find_by_codes(normalized_codes)
    role_map = {role.code: role for role in roles}
    missing = [code for code in normalized_codes if code not in role_map]
    if missing:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, f"角色不存在：{', '.join(missing)}")
    if active_only:
        inactive = [code for code, role in role_map.items() if not role.is_active]
        if inactive:
            raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, f"角色已停用，无法分配：{', '.join(sorted(inactive))}")
    return [role_map[code] for code in normalized_codes]


def user_has_role(user: UserAccount, role_code: str) -> bool:
    return any(link.role and link.role.is_active and link.role.code == role_code for link in user.role_links)


def ensure_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
