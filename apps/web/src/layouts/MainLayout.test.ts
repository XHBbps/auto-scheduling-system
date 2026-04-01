import { flushPromises, shallowMount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'

const postMock = vi.fn()
const clearAuthSessionMock = vi.fn()
const ensureAuthSessionMock = vi.fn()
const getAuthSessionStateMock = vi.fn()
const normalizeAuthRedirectPathMock = vi.fn((value: unknown, fallback = '/dashboard') => {
  if (typeof value !== 'string') return fallback
  const redirect = value.trim()
  if (!redirect || !redirect.startsWith('/') || redirect.startsWith('//')) return fallback
  return redirect
})
const successMessageMock = vi.fn()
const infoMessageMock = vi.fn()
const errorMessageMock = vi.fn()
const showStructuredConfirmDialogMock = vi.fn()

vi.mock('../utils/httpClient', () => ({
  default: {
    post: postMock,
  },
}))

vi.mock('../utils/authSession', () => ({
  AUTH_CHANGED_EVENT_NAME: 'auth-session-changed',
  clearAuthSession: clearAuthSessionMock,
  ensureAuthSession: ensureAuthSessionMock,
  getAuthSessionState: getAuthSessionStateMock,
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
  normalizeAuthRedirectPath: normalizeAuthRedirectPathMock,
}))

vi.mock('../utils/confirmDialog', () => ({
  showStructuredConfirmDialog: showStructuredConfirmDialogMock,
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: successMessageMock,
      info: infoMessageMock,
      error: errorMessageMock,
    },
    ElMessageBox: {
      confirm: vi.fn(),
    },
  }
})

const buildWrapper = async () => {
  vi.resetModules()
  const { createAppRouter } = await import('../router/index')
  const router = createAppRouter(createMemoryHistory())
  await router.push('/dashboard')
  await router.isReady()
  const component = (await import('./MainLayout.vue')).default

  const wrapper = shallowMount(component, {
    global: {
      plugins: [router],
      stubs: {
        transition: false,
        ElContainer: { template: '<div><slot /></div>' },
        ElAside: { template: '<aside><slot /></aside>' },
        ElHeader: { template: '<header><slot /></header>' },
        ElMain: { template: '<main><slot /></main>' },
        ElMenu: { template: '<nav><slot /></nav>' },
        ElMenuItem: { template: '<div><slot /></div>' },
        ElSubMenu: { template: '<div><slot name="title" /><slot /></div>' },
        ElTag: { template: '<span><slot /></span>' },
        ElIcon: { template: '<i><slot /></i>' },
        ElButton: { template: "<button @click=\"$emit('click')\"><slot /></button>" },
      },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('MainLayout interactions', () => {
  beforeEach(() => {
    postMock.mockResolvedValue({ total: 0, success_count: 0, fail_count: 0, message: '暂无可执行的排产订单' })
    clearAuthSessionMock.mockReset()
    ensureAuthSessionMock.mockResolvedValue(true)
    getAuthSessionStateMock.mockReturnValue({
      authenticated: true,
      user: null,
      expiresAt: null,
      expiresAtMs: null,
      roleCodes: ['admin'],
      roleNames: ['管理员'],
      permissionCodes: ['schedule.manage'],
    })
    normalizeAuthRedirectPathMock.mockClear()
    successMessageMock.mockClear()
    infoMessageMock.mockClear()
    errorMessageMock.mockClear()
    showStructuredConfirmDialogMock.mockReset()
    showStructuredConfirmDialogMock.mockResolvedValue('confirm')
    window.history.replaceState({}, '', '/')
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('clears auth session and redirects to admin auth after logout', async () => {
    const { wrapper, router } = await buildWrapper()
    const replaceSpy = vi.spyOn(router, 'replace')
    const setupState = (wrapper.vm as { $?: { setupState?: Record<string, unknown> } }).$?.setupState || {}

    expect(typeof setupState.handleLogout).toBe('function')

    await (setupState.handleLogout as () => Promise<void>)()
    await flushPromises()

    expect(postMock).toHaveBeenCalledWith('/api/auth/logout', {}, { silentError: true })
    expect(clearAuthSessionMock).toHaveBeenCalledTimes(1)
    expect(successMessageMock).toHaveBeenCalledWith('已退出登录')
    expect(replaceSpy).toHaveBeenCalledWith({
      name: 'AdminAuth',
      query: { redirect: '/dashboard' },
    })
  }, 10000)

  it('confirms before running one-click scheduling', async () => {
    const { wrapper } = await buildWrapper()
    const scheduleButton = wrapper.findAll('button').find((item) => item.text().includes('一键排产'))

    expect(scheduleButton).toBeTruthy()

    await scheduleButton!.trigger('click')
    await flushPromises()

    expect(showStructuredConfirmDialogMock).toHaveBeenCalledWith(
      expect.objectContaining({
        title: '一键排产确认',
        badge: '执行排产',
        headline: '确认立即执行一键排产吗？',
        confirmButtonText: '确认执行',
        customClass: 'app-confirm-message-box--sync',
      }),
    )
    expect(postMock).toHaveBeenCalledWith('/api/admin/schedule/run', {})
    expect(infoMessageMock).toHaveBeenCalledWith('暂无可执行的排产订单')
  }, 10000)
})
