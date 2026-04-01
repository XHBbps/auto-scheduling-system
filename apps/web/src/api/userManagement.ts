import request from '../utils/httpClient'
import type {
  AdminPermissionListResponse,
  AdminRoleDetail,
  AdminRoleItem,
  AdminRoleListResponse,
  AdminRolePermissionListResponse,
  AdminUserDetail,
  AdminUserItem,
  AdminUserListPageResponse,
} from '../types/apiModels'

const compactParams = <T extends Record<string, unknown>>(params: T) =>
  Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''),
  )

export const listAdminUsers = (params: {
  keyword?: string
  role_code?: string
  is_active?: boolean
  page_no: number
  page_size: number
}) => request.get<AdminUserListPageResponse>('/api/admin/users', { params: compactParams(params) })

export const getAdminUserDetail = (userId: number) =>
  request.get<AdminUserDetail>(`/api/admin/users/${userId}`)

export const createAdminUser = (payload: {
  username: string
  display_name: string
  password: string
  role_codes: string[]
  is_active: boolean
}) => request.post<AdminUserItem>('/api/admin/users', payload)

export const updateAdminUser = (
  userId: number,
  payload: { username: string; display_name: string },
) => request.put<AdminUserItem>(`/api/admin/users/${userId}`, payload)

export const updateAdminUserStatus = (userId: number, payload: { is_active: boolean }) =>
  request.patch<AdminUserItem>(`/api/admin/users/${userId}/status`, payload)

export const resetAdminUserPassword = (userId: number, payload: { new_password: string }) =>
  request.post<AdminUserItem>(`/api/admin/users/${userId}/reset-password`, payload)

export const updateAdminUserRoles = (userId: number, payload: { role_codes: string[] }) =>
  request.put<AdminUserItem>(`/api/admin/users/${userId}/roles`, payload)

export const listAdminRoles = () => request.get<AdminRoleListResponse>('/api/admin/roles')

export const getAdminRoleDetail = (roleId: number) =>
  request.get<AdminRoleDetail>(`/api/admin/roles/${roleId}`)

export const createAdminRole = (payload: {
  code: string
  name: string
  description?: string | null
  is_active: boolean
}) => request.post<AdminRoleItem>('/api/admin/roles', payload)

export const updateAdminRole = (
  roleId: number,
  payload: { name: string; description?: string | null },
) => request.put<AdminRoleItem>(`/api/admin/roles/${roleId}`, payload)

export const updateAdminRoleStatus = (roleId: number, payload: { is_active: boolean }) =>
  request.patch<AdminRoleItem>(`/api/admin/roles/${roleId}/status`, payload)

export const deleteAdminRole = (roleId: number) =>
  request.delete<void>(`/api/admin/roles/${roleId}`)

export const listAdminPermissions = () =>
  request.get<AdminPermissionListResponse>('/api/admin/permissions')

export const getAdminRolePermissions = (roleId: number) =>
  request.get<AdminRolePermissionListResponse>(`/api/admin/roles/${roleId}/permissions`)
