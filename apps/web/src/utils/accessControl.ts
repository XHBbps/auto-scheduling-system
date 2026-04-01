import type { RouteMeta } from 'vue-router'
import {
  hasAnyRequiredPermission,
  hasRequiredPermission,
  hasRequiredRole,
  type AuthSessionState,
} from './authSession'

export interface AccessRequirement {
  requiredRoles?: string[]
  requiredPermissions?: string[]
  requiredAnyPermissions?: string[]
}

export const isAdminSession = (state: AuthSessionState) => state.roleCodes.includes('admin')

export const hasPermissionCode = (state: AuthSessionState, permissionCode: string) =>
  isAdminSession(state) || state.permissionCodes.includes(permissionCode)

export const hasAnyPermissionCode = (state: AuthSessionState, permissionCodes: string[] = []) => {
  if (!permissionCodes.length) return true
  if (isAdminSession(state)) return true
  return permissionCodes.some((permissionCode) => state.permissionCodes.includes(permissionCode))
}

export const hasAccessRequirement = (state: AuthSessionState, requirement: AccessRequirement = {}) => {
  if (!state.authenticated) return false
  return (
    hasRequiredRole(state, requirement.requiredRoles || []) &&
    hasRequiredPermission(state, requirement.requiredPermissions || []) &&
    hasAnyRequiredPermission(state, requirement.requiredAnyPermissions || [])
  )
}

export const getRouteAccessRequirement = (meta: RouteMeta): AccessRequirement => ({
  requiredRoles: Array.isArray(meta.requiredRoles) ? meta.requiredRoles : [],
  requiredPermissions: Array.isArray(meta.requiredPermissions) ? meta.requiredPermissions : [],
  requiredAnyPermissions: Array.isArray((meta as RouteMeta & { requiredAnyPermissions?: string[] }).requiredAnyPermissions)
    ? (meta as RouteMeta & { requiredAnyPermissions?: string[] }).requiredAnyPermissions
    : [],
})
