import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'

vi.mock('../utils/authSession', () => ({
  ensureAuthSession: vi.fn(),
  hasRequiredRole: (state: { roleCodes: string[] }, requiredRoles: string[] = []) =>
    !requiredRoles.length || requiredRoles.every((role) => state.roleCodes.includes(role)),
  hasRequiredPermission: (state: { roleCodes: string[]; permissionCodes?: string[] }, requiredPermissions: string[] = []) =>
    !requiredPermissions.length ||
    state.roleCodes.includes('admin') ||
    requiredPermissions.every((permission) => (state.permissionCodes || []).includes(permission)),
  hasAnyRequiredPermission: (state: { roleCodes: string[]; permissionCodes?: string[] }, requiredAnyPermissions: string[] = []) =>
    !requiredAnyPermissions.length ||
    state.roleCodes.includes('admin') ||
    requiredAnyPermissions.some((permission) => (state.permissionCodes || []).includes(permission)),
  normalizeAuthRedirectPath: vi.fn((value: unknown, fallback = '/dashboard') => {
    if (typeof value !== 'string') return fallback
    const redirect = value.trim()
    if (!redirect || !redirect.startsWith('/') || redirect.startsWith('//')) return fallback
    if (redirect === '/admin-auth' || redirect === '/login') return fallback
    return redirect
  }),
}))

const buildRouter = async () => {
  vi.resetModules()
  const authSession = await import('../utils/authSession')
  const { createAppRouter } = await import('./index')
  const router = createAppRouter(createMemoryHistory())
  return {
    router,
    ensureAuthSessionMock: vi.mocked(authSession.ensureAuthSession),
  }
}

describe('router auth guard', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/')
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('redirects unauthenticated users to admin auth with redirect query', async () => {
    const { router, ensureAuthSessionMock } = await buildRouter()
    ensureAuthSessionMock.mockResolvedValue(false)

    await router.push('/dashboard')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('AdminAuth')
    expect(router.currentRoute.value.query.redirect).toBe('/dashboard')
  })

  it('passes route permission requirements into session validation', async () => {
    const { router, ensureAuthSessionMock } = await buildRouter()
    ensureAuthSessionMock.mockResolvedValue(true)

    await router.push('/sync-logs')
    await router.isReady()

    expect(ensureAuthSessionMock).toHaveBeenCalledWith({
      requiredRoles: [],
      requiredPermissions: ['sync.log.view'],
      requiredAnyPermissions: [],
    })
    expect(router.currentRoute.value.name).toBe('SyncLogList')
  })

  it('allows authenticated users to access protected routes', async () => {
    const { router, ensureAuthSessionMock } = await buildRouter()
    ensureAuthSessionMock.mockResolvedValue(true)

    await router.push('/dashboard')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('Dashboard')
  })

  it('redirects authenticated users away from admin auth to redirect target', async () => {
    const { router, ensureAuthSessionMock } = await buildRouter()
    ensureAuthSessionMock.mockResolvedValue(true)

    await router.push('/admin-auth?redirect=/issues')
    await router.isReady()

    expect(router.currentRoute.value.path).toBe('/issues')
  })
})

