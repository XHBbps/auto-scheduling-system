import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'

const postMock = vi.fn()
const ensureAuthSessionMock = vi.fn()
const formatAuthSessionExpiresAtDisplayMock = vi.fn()
const getAuthSessionStateMock = vi.fn()
const normalizeAuthRedirectPathMock = vi.fn((value: unknown, fallback = '/dashboard') => {
  if (typeof value !== 'string') return fallback
  const redirect = value.trim()
  if (!redirect || !redirect.startsWith('/') || redirect.startsWith('//')) return fallback
  if (redirect === '/admin-auth' || redirect === '/login') return fallback
  return redirect
})
const saveAuthSessionMock = vi.fn()
const successMessageMock = vi.fn()
const warningMessageMock = vi.fn()

vi.mock('../utils/httpClient', () => ({
  default: {
    post: postMock,
  },
}))

vi.mock('../utils/authSession', () => ({
  AUTH_CHANGED_EVENT_NAME: 'auth-session-changed',
  ensureAuthSession: ensureAuthSessionMock,
  formatAuthSessionExpiresAtDisplay: formatAuthSessionExpiresAtDisplayMock,
  getAuthSessionState: getAuthSessionStateMock,
  normalizeAuthRedirectPath: normalizeAuthRedirectPathMock,
  saveAuthSession: saveAuthSessionMock,
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: successMessageMock,
      warning: warningMessageMock,
      error: vi.fn(),
      info: vi.fn(),
    },
  }
})

const createAnonymousState = () => ({
  authenticated: false,
  user: null,
  expiresAt: null,
  expiresAtMs: null,
  roleCodes: [],
  roleNames: [],
})

const createAuthenticatedState = () => ({
  authenticated: true,
  user: {
    id: 1,
    username: 'admin',
    display_name: '系统管理员',
    is_active: true,
    roles: [{ code: 'admin', name: '管理员' }],
  },
  expiresAt: '2026-03-26T12:00:00Z',
  expiresAtMs: Date.now() + 60 * 60 * 1000,
  roleCodes: ['admin'],
  roleNames: ['管理员'],
})

const createSessionInfo = () => ({
  authenticated: true,
  user: createAuthenticatedState().user,
  expires_at: '2026-03-26T12:00:00Z',
})

type MockSessionState = ReturnType<typeof createAnonymousState> | ReturnType<typeof createAuthenticatedState>

const buildWrapper = async (routePath = '/admin-auth?redirect=/issues') => {
  vi.resetModules()
  const { createAppRouter } = await import('../router/index')
  const router = createAppRouter(createMemoryHistory())
  await router.push(routePath)
  await router.isReady()
  const { useAdminAccess } = await import('./useAdminAccess')

  const TestComponent = defineComponent({
    setup() {
      return useAdminAccess()
    },
    template: '<div />',
  })

  const wrapper = mount(TestComponent, {
    global: {
      plugins: [router],
      stubs: {
        transition: false,
      },
    },
  })

  await flushPromises()
  return { wrapper, router }
}

describe('useAdminAccess', () => {
  let currentState: MockSessionState = createAnonymousState()

  beforeEach(() => {
    currentState = createAnonymousState()
    postMock.mockReset()
    ensureAuthSessionMock.mockReset()
    formatAuthSessionExpiresAtDisplayMock.mockReset()
    getAuthSessionStateMock.mockImplementation(() => currentState)
    normalizeAuthRedirectPathMock.mockClear()
    saveAuthSessionMock.mockReset()
    successMessageMock.mockReset()
    warningMessageMock.mockReset()
    window.history.replaceState({}, '', '/')

    ensureAuthSessionMock.mockResolvedValue(false)
    formatAuthSessionExpiresAtDisplayMock.mockImplementation((value?: string | null) =>
      value ? '2026/03/26 20:00:00（北京时间）' : null,
    )
    saveAuthSessionMock.mockImplementation(() => {
      currentState = createAuthenticatedState()
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('submits login, saves session and redirects to original target', async () => {
    postMock.mockResolvedValue(createSessionInfo())
    const { wrapper, router } = await buildWrapper('/admin-auth?redirect=/issues')
    const replaceSpy = vi.spyOn(router, 'replace')

    wrapper.vm.username = '  admin  '
    wrapper.vm.password = 'secret'
    await nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(postMock).toHaveBeenCalledWith('/api/auth/login', {
      username: 'admin',
      password: 'secret',
    })
    expect(saveAuthSessionMock).toHaveBeenCalledTimes(1)
    expect(successMessageMock).toHaveBeenCalledWith('登录成功，会话有效期至 2026/03/26 20:00:00（北京时间）')
    expect(wrapper.vm.password).toBe('')
    expect(replaceSpy).toHaveBeenCalledWith('/issues')
  })

  it('clears password and stays on page when login fails', async () => {
    postMock.mockRejectedValue(new Error('登录失败'))
    const { wrapper, router } = await buildWrapper('/admin-auth?redirect=/issues')
    const replaceSpy = vi.spyOn(router, 'replace')

    wrapper.vm.username = 'admin'
    wrapper.vm.password = 'wrong-password'
    await nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(postMock).toHaveBeenCalledTimes(1)
    expect(wrapper.vm.password).toBe('')
    expect(saveAuthSessionMock).not.toHaveBeenCalled()
    expect(successMessageMock).not.toHaveBeenCalled()
    expect(replaceSpy).not.toHaveBeenCalledWith('/issues')
  })

  it('warns and prevents submit when username or password is empty', async () => {
    const { wrapper } = await buildWrapper('/admin-auth')

    wrapper.vm.username = ''
    wrapper.vm.password = ''
    await wrapper.vm.handleSubmit()
    expect(warningMessageMock).toHaveBeenCalledWith('请输入登录账号')

    warningMessageMock.mockClear()
    wrapper.vm.username = 'admin'
    wrapper.vm.password = ''
    await wrapper.vm.handleSubmit()
    expect(warningMessageMock).toHaveBeenCalledWith('请输入登录密码')
    expect(postMock).not.toHaveBeenCalled()
  })

  it('redirects away from login page when an active admin session already exists', async () => {
    currentState = createAuthenticatedState()
    ensureAuthSessionMock.mockResolvedValue(true)
    const { router } = await buildWrapper('/admin-auth?redirect=/part-schedules')

    expect(router.currentRoute.value.path).toBe('/part-schedules')
  })

  it('builds active session summary from current session state', async () => {
    currentState = createAuthenticatedState()
    const { wrapper } = await buildWrapper('/admin-auth')

    expect(wrapper.vm.activeSessionSummary).toContain('当前已登录用户：系统管理员')
    expect(wrapper.vm.activeSessionSummary).toContain('会话有效期至 2026/03/26 20:00:00（北京时间）')
  })
})
