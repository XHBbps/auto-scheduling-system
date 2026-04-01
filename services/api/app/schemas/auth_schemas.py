from __future__ import annotations

from pydantic import BaseModel, Field


class RoleItemResponse(BaseModel):
    code: str = Field(description="角色英文编码")
    name: str = Field(description="角色中文名称")


class AuthenticatedUserResponse(BaseModel):
    id: int = Field(description="用户 ID")
    username: str = Field(description="登录账号")
    display_name: str = Field(description="显示名称")
    is_active: bool = Field(description="是否启用")
    last_login_at: str | None = Field(default=None, description="最近登录时间，UTC ISO8601")
    created_at: str | None = Field(default=None, description="创建时间，UTC ISO8601")
    updated_at: str | None = Field(default=None, description="更新时间，UTC ISO8601")
    roles: list[RoleItemResponse] = Field(default_factory=list, description="用户角色列表")
    permission_codes: list[str] = Field(default_factory=list, description="当前用户已拥有的权限点编码列表")


class AuthLoginRequest(BaseModel):
    username: str = Field(description="登录账号")
    password: str = Field(description="登录密码")


class AuthSessionInfoResponse(BaseModel):
    authenticated: bool = Field(description="是否已认证")
    user: AuthenticatedUserResponse | None = Field(default=None, description="当前登录用户")
    expires_at: str | None = Field(default=None, description="会话到期时间，UTC ISO8601")


class UserCreateRequest(BaseModel):
    username: str = Field(description="新建用户登录账号")
    display_name: str = Field(description="用户显示名称")
    password: str = Field(min_length=8, max_length=128, description="初始密码，8-128 字符")
    role_codes: list[str] = Field(default_factory=list, description="角色编码列表，至少传入一个角色编码")
    is_active: bool = Field(default=True, description="是否启用")


class UserUpdateRequest(BaseModel):
    username: str = Field(description="登录账号")
    display_name: str = Field(description="显示名称")


class UserStatusUpdateRequest(BaseModel):
    is_active: bool = Field(description="是否启用该用户")


class UserPasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128, description="新密码，8-128 字符")


class UserRoleUpdateRequest(BaseModel):
    role_codes: list[str] = Field(default_factory=list, description="角色编码列表")


class AdminUserItemResponse(AuthenticatedUserResponse):
    session_source: str | None = Field(default=None, description="最近访问来源，预留字段")


class AdminUserDetailResponse(AdminUserItemResponse):
    pass


class AdminUserListPageResponse(BaseModel):
    total: int = Field(description="用户总数")
    page_no: int = Field(description="当前页码")
    page_size: int = Field(description="当前分页大小")
    items: list[AdminUserItemResponse] = Field(default_factory=list, description="当前页用户列表")


class AdminPermissionItemResponse(BaseModel):
    id: int = Field(description="权限 ID")
    code: str = Field(description="权限英文编码")
    name: str = Field(description="权限中文名称")
    module_name: str = Field(description="所属模块中文名称")
    description: str | None = Field(default=None, description="权限说明")
    sort_order: int = Field(description="展示排序值")
    is_active: bool = Field(description="是否启用")
    is_system: bool = Field(description="是否系统内置")
    created_at: str | None = Field(default=None, description="创建时间，UTC ISO8601")
    updated_at: str | None = Field(default=None, description="更新时间，UTC ISO8601")


class AdminPermissionListResponse(BaseModel):
    items: list[AdminPermissionItemResponse] = Field(default_factory=list, description="权限目录列表")


class RoleCreateRequest(BaseModel):
    code: str = Field(description="角色英文编码，用于系统内部标识")
    name: str = Field(description="角色中文名称")
    description: str | None = Field(default=None, description="角色说明")
    is_active: bool = Field(default=True, description="是否启用")


class RoleUpdateRequest(BaseModel):
    name: str = Field(description="角色中文名称")
    description: str | None = Field(default=None, description="角色说明")


class RoleStatusUpdateRequest(BaseModel):
    is_active: bool = Field(description="是否启用该角色")


class RolePermissionUpdateRequest(BaseModel):
    permission_codes: list[str] = Field(default_factory=list, description="权限编码列表；传空表示清空当前角色的所有自定义权限")


class AdminRoleItemResponse(BaseModel):
    id: int = Field(description="角色 ID")
    code: str = Field(description="角色英文编码")
    name: str = Field(description="角色中文名称")
    description: str | None = Field(default=None, description="角色说明")
    is_active: bool = Field(description="是否启用")
    is_system: bool = Field(description="是否系统内置")
    assigned_user_count: int = Field(description="已绑定用户数")
    permission_count: int = Field(description="已绑定权限数")
    created_at: str | None = Field(default=None, description="创建时间，UTC ISO8601")
    updated_at: str | None = Field(default=None, description="更新时间，UTC ISO8601")


class AdminRoleDetailResponse(AdminRoleItemResponse):
    permissions: list[AdminPermissionItemResponse] = Field(default_factory=list, description="角色已绑定权限列表")


class AdminRoleListResponse(BaseModel):
    items: list[AdminRoleItemResponse] = Field(default_factory=list, description="角色列表")


class AdminRolePermissionListResponse(BaseModel):
    role_id: int = Field(description="角色 ID")
    role_code: str = Field(description="角色英文编码")
    role_name: str = Field(description="角色中文名称")
    items: list[AdminPermissionItemResponse] = Field(default_factory=list, description="角色绑定权限列表")


class AdminPermissionMatrixRoleItemResponse(BaseModel):
    id: int = Field(description="角色 ID")
    code: str = Field(description="角色英文编码")
    name: str = Field(description="角色中文名称")
    is_active: bool = Field(description="是否启用")
    is_system: bool = Field(description="是否系统内置")
    assigned_user_count: int = Field(description="已绑定用户数")
    permission_count: int = Field(description="已绑定权限数")


class AdminPermissionMatrixCellResponse(BaseModel):
    role_id: int = Field(description="角色 ID")
    role_code: str = Field(description="角色英文编码")
    assigned: bool = Field(description="当前权限是否已分配给该角色")


class AdminPermissionMatrixPermissionItemResponse(AdminPermissionItemResponse):
    role_bindings: list[AdminPermissionMatrixCellResponse] = Field(default_factory=list, description="权限与角色的绑定矩阵")


class AdminPermissionMatrixResponse(BaseModel):
    roles: list[AdminPermissionMatrixRoleItemResponse] = Field(default_factory=list, description="矩阵中的角色列表")
    permissions: list[AdminPermissionMatrixPermissionItemResponse] = Field(default_factory=list, description="矩阵中的权限列表")


class AdminPermissionRouteLinkItemResponse(BaseModel):
    path: str = Field(description="受保护接口路径")
    methods: list[str] = Field(default_factory=list, description="接口支持的 HTTP 方法列表")
    tags: list[str] = Field(default_factory=list, description="接口所属标签列表")
    summary: str | None = Field(default=None, description="接口摘要")
    description: str | None = Field(default=None, description="接口说明")


class AdminPermissionLinkageItemResponse(AdminPermissionItemResponse):
    linked_routes: list[AdminPermissionRouteLinkItemResponse] = Field(default_factory=list, description="该权限点关联的后端接口列表")


class AdminPermissionLinkageResponse(BaseModel):
    items: list[AdminPermissionLinkageItemResponse] = Field(default_factory=list, description="权限点与后端接口联动清单")
