const AUTH_SESSION_KEY = 'auth_session_state'
const AUTH_CHANGED_EVENT = 'auth-session-changed'
const AUTH_SESSION_INFO_PATH = '/api/auth/session'
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const DISPLAY_TIME_ZONE = 'Asia/Shanghai'

import type { RoleInfo, AuthenticatedUser } from '../types/apiModels'

let ensurePromise: Promise<boolean> | null = null

export type { RoleInfo, AuthenticatedUser }

export interface AuthSessionState {
  authenticated: boolean
  user: AuthenticatedUser | null
  expiresAt: string | null
  expiresAtMs: number | null
  roleCodes: string[]
  roleNames: string[]
  permissionCodes: string[]
}

interface AuthSessionPayload {
  authenticated?: boolean
  user?: AuthenticatedUser | null
  expires_at?: string | null
}

interface EnsureAuthSessionOptions {
  forceRefresh?: boolean
  requiredRoles?: string[]
  requiredPermissions?: string[]
  requiredAnyPermissions?: string[]
}

const DEFAULT_AUTH_REDIRECT = '/dashboard'

const isAbsoluteUrl = (value: string) => /^https?:\/\//i.test(value)

const buildApiUrl = (path: string) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  if (!isAbsoluteUrl(API_BASE_URL)) {
    return normalizedPath
  }
  return `${API_BASE_URL}${normalizedPath}`
}

const getStorage = (): Storage | null => {
  if (typeof window === 'undefined') {
    return null
  }
  try {
    return window.localStorage
  } catch {
    return null
  }
}

const emitAuthChanged = () => {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT))
}

const parseExpiresAt = (value: unknown): number | null => {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  if (!trimmed) return null
  const normalized = trimmed.includes(' ') && !trimmed.includes('T') ? trimmed.replace(' ', 'T') : trimmed
  const parsed = Date.parse(normalized)
  return Number.isNaN(parsed) ? null : parsed
}

const createEmptyState = (): AuthSessionState => ({
  authenticated: false,
  user: null,
  expiresAt: null,
  expiresAtMs: null,
  roleCodes: [],
  roleNames: [],
  permissionCodes: [],
})

const normalizeUser = (value: unknown): AuthenticatedUser | null => {
  if (!value || typeof value !== 'object') return null
  const raw = value as Partial<AuthenticatedUser>
  const roles = Array.isArray(raw.roles)
    ? raw.roles
        .filter((item): item is RoleInfo => Boolean(item && typeof item.code === 'string' && typeof item.name === 'string'))
        .map((item) => ({ code: item.code, name: item.name }))
    : []
  const permissionCodes = Array.isArray((raw as { permission_codes?: unknown }).permission_codes)
    ? (raw as { permission_codes: unknown[] }).permission_codes.filter(
        (item): item is string => typeof item === 'string' && item.trim().length > 0,
      )
    : []
  if (typeof raw.display_name !== 'string' || typeof raw.username !== 'string' || typeof raw.id !== 'number') {
    return null
  }
  return {
    id: raw.id,
    username: raw.username,
    display_name: raw.display_name,
    is_active: raw.is_active !== false,
    last_login_at: raw.last_login_at ?? null,
    created_at: raw.created_at ?? null,
    updated_at: raw.updated_at ?? null,
    roles,
    permission_codes: permissionCodes,
  }
}

const normalizeState = (value: unknown): AuthSessionState => {
  if (!value || typeof value !== 'object') return createEmptyState()
  const raw = value as Partial<AuthSessionState>
  const user = normalizeUser(raw.user)
  const expiresAt = typeof raw.expiresAt === 'string' && raw.expiresAt ? raw.expiresAt : null
  const expiresAtMs =
    typeof raw.expiresAtMs === 'number' && Number.isFinite(raw.expiresAtMs)
      ? raw.expiresAtMs
      : parseExpiresAt(expiresAt)
  const roleCodes = user?.roles.map((role) => role.code) ?? []
  const roleNames = user?.roles.map((role) => role.name) ?? []
  const permissionCodes = user?.permission_codes ?? []
  return {
    authenticated: Boolean(raw.authenticated) && Boolean(user) && Boolean(expiresAtMs && expiresAtMs > Date.now()),
    user,
    expiresAt,
    expiresAtMs,
    roleCodes,
    roleNames,
    permissionCodes,
  }
}

export const getAuthSessionState = (): AuthSessionState => {
  const storage = getStorage()
  if (!storage) return createEmptyState()
  const raw = storage.getItem(AUTH_SESSION_KEY)
  if (!raw) return createEmptyState()
  try {
    return normalizeState(JSON.parse(raw))
  } catch {
    return createEmptyState()
  }
}

export const hasActiveAuthSession = (): boolean => getAuthSessionState().authenticated

export const hasRequiredRole = (state: AuthSessionState, requiredRoles: string[] = []): boolean => {
  if (!requiredRoles.length) return true
  return requiredRoles.every((role) => state.roleCodes.includes(role))
}

export const hasRequiredPermission = (state: AuthSessionState, requiredPermissions: string[] = []): boolean => {
  if (!requiredPermissions.length) return true
  if (state.roleCodes.includes('admin')) return true
  return requiredPermissions.every((permission) => state.permissionCodes.includes(permission))
}

export const hasAnyRequiredPermission = (state: AuthSessionState, requiredAnyPermissions: string[] = []): boolean => {
  if (!requiredAnyPermissions.length) return true
  if (state.roleCodes.includes('admin')) return true
  return requiredAnyPermissions.some((permission) => state.permissionCodes.includes(permission))
}

export const formatAuthSessionExpiresAtDisplay = (value: string | null | undefined): string | null => {
  const expiresAtMs = parseExpiresAt(value)
  if (!expiresAtMs) return null
  try {
    const formatter = new Intl.DateTimeFormat('zh-CN', {
      timeZone: DISPLAY_TIME_ZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
    return `${formatter.format(new Date(expiresAtMs))}（北京时间）`
  } catch {
    return new Date(expiresAtMs).toLocaleString('zh-CN', { hour12: false })
  }
}

export const normalizeAuthRedirectPath = (value: unknown, fallback = DEFAULT_AUTH_REDIRECT): string => {
  if (typeof value !== 'string') return fallback
  const redirect = value.trim()
  if (!redirect || !redirect.startsWith('/')) return fallback
  if (redirect.startsWith('//')) return fallback
  if (isAbsoluteUrl(redirect)) return fallback
  if (redirect === '/admin-auth' || redirect === '/login') return fallback
  return redirect
}

export const saveAuthSession = (payload: AuthSessionPayload) => {
  const storage = getStorage()
  if (!storage) return
  const user = normalizeUser(payload.user)
  const expiresAt = typeof payload.expires_at === 'string' ? payload.expires_at : null
  const expiresAtMs = parseExpiresAt(expiresAt)
  const state: AuthSessionState = {
    authenticated: Boolean(payload.authenticated) && Boolean(user) && Boolean(expiresAtMs && expiresAtMs > Date.now()),
    user,
    expiresAt,
    expiresAtMs,
    roleCodes: user?.roles.map((role) => role.code) ?? [],
    roleNames: user?.roles.map((role) => role.name) ?? [],
    permissionCodes: user?.permission_codes ?? [],
  }
  storage.setItem(AUTH_SESSION_KEY, JSON.stringify(state))
  emitAuthChanged()
}

export const clearAuthSession = () => {
  const storage = getStorage()
  if (!storage) return
  storage.removeItem(AUTH_SESSION_KEY)
  emitAuthChanged()
}

export const syncAuthSessionFromServer = async (): Promise<AuthSessionState> => {
  if (typeof window === 'undefined') return createEmptyState()
  const fallbackState = getAuthSessionState()
  try {
    const response = await window.fetch(buildApiUrl(AUTH_SESSION_INFO_PATH), {
      method: 'GET',
      credentials: 'include',
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        clearAuthSession()
        return createEmptyState()
      }
      return fallbackState
    }
    const body = (await response.json()) as { code?: number; data?: AuthSessionPayload }
    if (body?.code !== 0) return fallbackState
    if (!body?.data?.authenticated || !body.data.user) {
      clearAuthSession()
      return createEmptyState()
    }
    saveAuthSession(body.data)
    return getAuthSessionState()
  } catch {
    return fallbackState
  }
}

export const ensureAuthSession = async (options: EnsureAuthSessionOptions = {}): Promise<boolean> => {
  const { forceRefresh = false, requiredRoles = [], requiredPermissions = [], requiredAnyPermissions = [] } = options
  const cachedState = getAuthSessionState()
  if (
    !forceRefresh &&
    cachedState.authenticated &&
    hasRequiredRole(cachedState, requiredRoles) &&
    hasRequiredPermission(cachedState, requiredPermissions) &&
    hasAnyRequiredPermission(cachedState, requiredAnyPermissions)
  ) {
    return true
  }
  // If there's already a sync in flight, wait for it then re-check permissions
  // against the freshly synced state instead of reusing the original promise's
  // permission check result (which may have been for different permissions).
  if (ensurePromise) {
    await ensurePromise
    const refreshedState = getAuthSessionState()
    return (
      refreshedState.authenticated &&
      hasRequiredRole(refreshedState, requiredRoles) &&
      hasRequiredPermission(refreshedState, requiredPermissions) &&
      hasAnyRequiredPermission(refreshedState, requiredAnyPermissions)
    )
  }
  ensurePromise = (async () => {
    const state = await syncAuthSessionFromServer()
    return state.authenticated && hasRequiredRole(state, requiredRoles) && hasRequiredPermission(state, requiredPermissions) && hasAnyRequiredPermission(state, requiredAnyPermissions)
  })().finally(() => {
    ensurePromise = null
  })
  return ensurePromise
}

export const AUTH_CHANGED_EVENT_NAME = AUTH_CHANGED_EVENT
