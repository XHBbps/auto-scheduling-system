import { beforeEach, describe, expect, it, vi } from 'vitest'

const clearAuthSessionMock = vi.fn()
const errorMessageMock = vi.fn()

let responseErrorHandler: ((error: any) => Promise<never>) | undefined

vi.mock('axios', () => {
  const useRequest = vi.fn((handler) => handler)
  const useResponse = vi.fn((_fulfilled, rejected) => {
    responseErrorHandler = rejected
  })

  return {
    default: {
      create: vi.fn(() => ({
        interceptors: {
          request: { use: useRequest },
          response: { use: useResponse },
        },
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
      })),
    },
  }
})

vi.mock('element-plus', () => ({
  ElMessage: {
    error: errorMessageMock,
  },
}))

vi.mock('./authSession', () => ({
  clearAuthSession: clearAuthSessionMock,
}))

describe('httpClient protected auth handling', () => {
  beforeEach(async () => {
    vi.resetModules()
    clearAuthSessionMock.mockReset()
    errorMessageMock.mockReset()
    responseErrorHandler = undefined
    await import('./httpClient')
  })

  it.each([
    '/api/dashboard/overview',
    '/api/schedules',
    '/api/schedules/123',
    '/api/part-schedules',
    '/api/part-schedules/123',
    '/api/issues',
  ])('clears local auth session for protected endpoint %s on 401', async (url) => {
    await expect(
      responseErrorHandler?.({
        config: { url },
        response: { status: 401, data: { message: '登录失效' } },
      }),
    ).rejects.toMatchObject({ status: 401 })

    expect(clearAuthSessionMock).toHaveBeenCalledTimes(1)
    expect(errorMessageMock).toHaveBeenCalledWith('登录状态已失效，请重新登录')
  })

  it('clears local auth session for protected endpoint on 403', async () => {
    await expect(
      responseErrorHandler?.({
        config: { url: '/api/schedules/321' },
        response: { status: 403, data: { message: '无权限' } },
      }),
    ).rejects.toMatchObject({ status: 403 })

    expect(clearAuthSessionMock).toHaveBeenCalledTimes(1)
    expect(errorMessageMock).toHaveBeenCalledWith('当前账号无权访问该页面')
  })

  it('does not clear auth session for non-protected endpoint', async () => {
    await expect(
      responseErrorHandler?.({
        config: { url: '/api/auth/login' },
        response: { status: 401, data: { message: '登录失败' } },
      }),
    ).rejects.toMatchObject({ status: 401 })

    expect(clearAuthSessionMock).not.toHaveBeenCalled()
    expect(errorMessageMock).toHaveBeenCalledWith('登录失败')
  })

  it('does not show duplicate auth toast for silent protected request', async () => {
    await expect(
      responseErrorHandler?.({
        config: { url: '/api/dashboard/overview', silentError: true },
        response: { status: 401, data: { message: '登录失效' } },
      }),
    ).rejects.toMatchObject({ status: 401 })

    expect(clearAuthSessionMock).toHaveBeenCalledTimes(1)
    expect(errorMessageMock).not.toHaveBeenCalled()
  })
})
