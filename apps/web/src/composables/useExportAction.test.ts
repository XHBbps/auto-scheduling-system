import { beforeEach, describe, expect, it, vi } from 'vitest'

const ensureAuthSessionMock = vi.fn()
const getAuthSessionStateMock = vi.fn()
const downloadBlobMock = vi.fn()
const confirmMock = vi.fn()
const pushMock = vi.fn()
const successMessageMock = vi.fn()
const errorMessageMock = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({
    fullPath: '/schedules?order_no=SOUL-001',
  }),
  useRouter: () => ({
    push: pushMock,
  }),
}))

vi.mock('../utils/authSession', () => ({
  ensureAuthSession: ensureAuthSessionMock,
  getAuthSessionState: getAuthSessionStateMock,
}))

vi.mock('../utils/download', () => ({
  downloadBlob: downloadBlobMock,
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: successMessageMock,
    error: errorMessageMock,
  },
  ElMessageBox: {
    confirm: confirmMock,
  },
}))

describe('useExportAction', () => {
  beforeEach(() => {
    ensureAuthSessionMock.mockReset()
    getAuthSessionStateMock.mockReset()
    downloadBlobMock.mockReset()
    confirmMock.mockReset()
    pushMock.mockReset()
    successMessageMock.mockReset()
    errorMessageMock.mockReset()
    getAuthSessionStateMock.mockReturnValue({ authenticated: false })
  })

  it('confirms export, downloads file and shows success feedback', async () => {
    confirmMock.mockResolvedValue('confirm')
    ensureAuthSessionMock.mockResolvedValue(true)
    const requestMock = vi.fn().mockResolvedValue(new Blob(['ok']))

    const { useExportAction } = await import('./useExportAction')
    const { exporting, runConfirmedExport } = useExportAction()

    await expect(
      runConfirmedExport({
        confirmTitle: '导出整机排产列表',
        confirmMessage: '确认导出吗？',
        fallbackFilename: '整机排产列表.xlsx',
        successMessage: '整机排产列表导出成功，已开始下载',
        request: requestMock,
      }),
    ).resolves.toBe(true)

    expect(ensureAuthSessionMock).toHaveBeenCalledWith({ forceRefresh: true, requiredPermissions: ['export.view'] })
    expect(requestMock).toHaveBeenCalledTimes(1)
    expect(downloadBlobMock).toHaveBeenCalledWith(expect.any(Blob), '整机排产列表.xlsx')
    expect(successMessageMock).toHaveBeenCalledWith('整机排产列表导出成功，已开始下载')
    expect(exporting.value).toBe(false)
  })

  it('does nothing when export confirmation is canceled', async () => {
    confirmMock.mockRejectedValue('cancel')
    const requestMock = vi.fn()

    const { useExportAction } = await import('./useExportAction')
    const { runConfirmedExport } = useExportAction()

    await expect(
      runConfirmedExport({
        confirmTitle: '导出整机排产列表',
        confirmMessage: '确认导出吗？',
        fallbackFilename: '整机排产列表.xlsx',
        request: requestMock,
      }),
    ).resolves.toBe(false)

    expect(ensureAuthSessionMock).not.toHaveBeenCalled()
    expect(requestMock).not.toHaveBeenCalled()
    expect(downloadBlobMock).not.toHaveBeenCalled()
  })

  it('redirects to admin auth only when local session is not authenticated', async () => {
    confirmMock.mockResolvedValue('confirm')
    ensureAuthSessionMock.mockResolvedValue(false)
    getAuthSessionStateMock.mockReturnValue({ authenticated: false })
    const requestMock = vi.fn()

    const { useExportAction } = await import('./useExportAction')
    const { runConfirmedExport } = useExportAction()

    await expect(
      runConfirmedExport({
        confirmTitle: '导出整机排产列表',
        confirmMessage: '确认导出吗？',
        fallbackFilename: '整机排产列表.xlsx',
        request: requestMock,
      }),
    ).resolves.toBe(false)

    expect(requestMock).not.toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalledWith({
      name: 'AdminAuth',
      query: {
        redirect: '/schedules?order_no=SOUL-001',
      },
    })
  })

  it('shows forbidden feedback instead of redirecting when session is authenticated but lacks export permission', async () => {
    confirmMock.mockResolvedValue('confirm')
    ensureAuthSessionMock.mockResolvedValue(false)
    getAuthSessionStateMock.mockReturnValue({ authenticated: true })
    const requestMock = vi.fn()

    const { useExportAction } = await import('./useExportAction')
    const { runConfirmedExport } = useExportAction()

    await expect(
      runConfirmedExport({
        confirmTitle: '导出整机排产列表',
        confirmMessage: '确认导出吗？',
        fallbackFilename: '整机排产列表.xlsx',
        request: requestMock,
      }),
    ).resolves.toBe(false)

    expect(requestMock).not.toHaveBeenCalled()
    expect(errorMessageMock).toHaveBeenCalledWith('当前账号无权限导出所选数据')
    expect(pushMock).not.toHaveBeenCalled()
  })

  it.each([
    [401, '登录状态已失效，请重新登录后再导出', true],
    [403, '当前账号无权限导出所选数据', false],
  ])('shows proper feedback when export request returns %s', async (status, message, shouldRedirect) => {
    confirmMock.mockResolvedValue('confirm')
    ensureAuthSessionMock.mockResolvedValue(true)
    const requestMock = vi.fn().mockRejectedValue(Object.assign(new Error('export failed'), { status }))

    const { useExportAction } = await import('./useExportAction')
    const { exporting, runConfirmedExport } = useExportAction()

    await expect(
      runConfirmedExport({
        confirmTitle: '导出整机排产列表',
        confirmMessage: '确认导出吗？',
        fallbackFilename: '整机排产列表.xlsx',
        request: requestMock,
      }),
    ).resolves.toBe(false)

    expect(errorMessageMock).toHaveBeenCalledWith(message)
    expect(downloadBlobMock).not.toHaveBeenCalled()
    expect(exporting.value).toBe(false)

    if (shouldRedirect) {
      expect(pushMock).toHaveBeenCalledWith({
        name: 'AdminAuth',
        query: {
          redirect: '/schedules?order_no=SOUL-001',
        },
      })
    } else {
      expect(pushMock).not.toHaveBeenCalled()
    }
  })
})
