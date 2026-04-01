import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearAuthSession,
  ensureAuthSession,
  getAuthSessionState,
  normalizeAuthRedirectPath,
  saveAuthSession,
} from './authSession'

const createUserPayload = () => ({
  id: 1,
  username: 'admin',
  display_name: '系统管理员',
  is_active: true,
  roles: [{ code: 'admin', name: '管理员' }],
  permission_codes: ['user.view', 'schedule.manage'],
})

const createFutureIso = () => new Date(Date.now() + 60 * 60 * 1000).toISOString()

describe('authSession', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.unstubAllGlobals()
  })

  afterEach(() => {
    clearAuthSession()
    vi.unstubAllGlobals()
  })

  it('normalizes invalid redirect paths to fallback', () => {
    expect(normalizeAuthRedirectPath('/issues')).toBe('/issues')
    expect(normalizeAuthRedirectPath('/login')).toBe('/dashboard')
    expect(normalizeAuthRedirectPath('https://example.com')).toBe('/dashboard')
    expect(normalizeAuthRedirectPath('//example.com')).toBe('/dashboard')
    expect(normalizeAuthRedirectPath(undefined, '/part-schedules')).toBe('/part-schedules')
  })

  it('saves and clears an authenticated admin session', () => {
    saveAuthSession({
      authenticated: true,
      user: createUserPayload(),
      expires_at: createFutureIso(),
    })

    const state = getAuthSessionState()
    expect(state.authenticated).toBe(true)
    expect(state.roleCodes).toEqual(['admin'])
    expect(state.permissionCodes).toEqual(['user.view', 'schedule.manage'])
    expect(state.user?.display_name).toBe('系统管理员')

    clearAuthSession()
    expect(getAuthSessionState().authenticated).toBe(false)
  })

  it.each([401, 403])('clears local session when server refresh returns %s', async (status) => {
    saveAuthSession({
      authenticated: true,
      user: createUserPayload(),
      expires_at: createFutureIso(),
    })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(null, {
          status,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(ensureAuthSession({ forceRefresh: true, requiredRoles: ['admin'] })).resolves.toBe(false)
    expect(getAuthSessionState().authenticated).toBe(false)
    expect(getAuthSessionState().user).toBeNull()
  })

  it('refreshes session from server and validates required roles and permissions', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: 0,
            data: {
              authenticated: true,
              user: createUserPayload(),
              expires_at: createFutureIso(),
            },
          }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      ),
    )

    await expect(
      ensureAuthSession({
        forceRefresh: true,
        requiredRoles: ['admin'],
        requiredPermissions: ['user.view'],
        requiredAnyPermissions: ['schedule.view', 'schedule.manage'],
      }),
    ).resolves.toBe(true)
    expect(getAuthSessionState().authenticated).toBe(true)
    expect(getAuthSessionState().roleCodes).toContain('admin')
    expect(getAuthSessionState().permissionCodes).toContain('user.view')
  })
})
