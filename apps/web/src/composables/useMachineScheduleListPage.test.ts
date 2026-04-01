import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const postMock = vi.fn()
const pushMock = vi.fn()
const alertMock = vi.fn()
const successMessageMock = vi.fn()
const errorMessageMock = vi.fn()
const warningMessageMock = vi.fn()
const ensureAuthSessionMock = vi.fn()
const getAuthSessionStateMock = vi.fn()
const feedbackState = ref<'loading' | 'ready' | 'empty' | 'error' | 'auth' | 'forbidden' | 'disabled'>('ready')

vi.mock('../utils/httpClient', () => ({
  default: {
    get: getMock,
    post: postMock,
  },
}))

vi.mock('../utils/requestCache', () => ({
  getCachedAsync: vi.fn(async (_key, _ttl, loader) => loader()),
}))

vi.mock('../utils/performance', () => ({
  measureAsync: vi.fn(async (_scope, _label, task) => task()),
}))

vi.mock('../utils/authSession', () => ({
  ensureAuthSession: ensureAuthSessionMock,
  getAuthSessionState: getAuthSessionStateMock,
}))

vi.mock('../utils/accessControl', () => ({
  hasPermissionCode: vi.fn((state, permissionCode) => state.roleCodes?.includes('admin') || state.permissionCodes?.includes(permissionCode)),
}))

vi.mock('./useExportAction', () => ({
  useExportAction: () => ({
    exporting: ref(false),
    runConfirmedExport: vi.fn(),
  }),
}))

vi.mock('./useTableFeedbackState', () => ({
  useTableFeedbackState: () => ({
    tableFeedbackState: feedbackState,
    showLoadingState: vi.fn(() => {
      feedbackState.value = 'loading'
    }),
    showEmptyState: vi.fn(() => {
      feedbackState.value = 'ready'
    }),
    showErrorState: vi.fn(() => {
      feedbackState.value = 'error'
    }),
  }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  useRoute: () => ({
    fullPath: '/schedules',
    query: {
      contract_no: 'HT-001',
      warning_level: 'abnormal',
      schedule_bucket: 'risk',
      date_from: '2026-03-01',
      date_to: '2026-03-31',
    },
  }),
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: successMessageMock,
      error: errorMessageMock,
      warning: warningMessageMock,
      info: vi.fn(),
    },
    ElMessageBox: {
      alert: alertMock,
      confirm: vi.fn(),
    },
  }
})

const buildWrapper = async () => {
  const { useMachineScheduleListPage } = await import('./useMachineScheduleListPage')

  const TestComponent = defineComponent({
    setup() {
      return useMachineScheduleListPage()
    },
    template: '<div />',
  })

  const wrapper = mount(TestComponent)
  await flushPromises()
  return wrapper
}

describe('useMachineScheduleListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    feedbackState.value = 'ready'
    window.localStorage.clear()
    window.localStorage.setItem('schedule-list-visible-columns', JSON.stringify(['custom_no', 'warning_level']))
    ensureAuthSessionMock.mockResolvedValue(true)
    getAuthSessionStateMock.mockReturnValue({
      authenticated: true,
      roleCodes: ['admin'],
      permissionCodes: ['schedule.manage'],
    })
    getMock.mockImplementation((url: string, options?: { params?: Record<string, unknown> }) => {
      if (url === '/api/schedules/options/product-series') {
        return Promise.resolve(['S1', 'S2'])
      }
      if (url === '/api/schedules') {
        return Promise.resolve({
          total: 1,
          items: [
            {
              order_line_id: 101,
              contract_no: 'HT-001',
              order_no: 'SO-001',
              customer_name: '扬力',
              product_model: 'YL-160',
              quantity: 2,
              schedule_status: 'scheduled_stale',
              warning_level: 'abnormal',
            },
          ],
          _params: options?.params,
        })
      }
      return Promise.resolve([])
    })
    postMock.mockResolvedValue({
      success: false,
      message: '校验未通过',
      validation_items: [{ level: 'blocking', label: 'BOM', message: '缺少 BOM' }],
    })
  })

  it('hydrates route query, loads cached options, and fetches list data with mapped params', async () => {
    const wrapper = await buildWrapper()

    expect(wrapper.vm.searchForm.contractNo).toBe('HT-001')
    expect(wrapper.vm.searchForm.warningLevel).toBe('abnormal')
    expect(wrapper.vm.dateRange).toEqual(['2026-03-01', '2026-03-31'])
    expect(wrapper.vm.productSeriesOptions).toEqual(['S1', 'S2'])
    expect(wrapper.vm.visibleColumnKeys).toEqual(['custom_no', 'warning_level'])
    expect(wrapper.vm.tableData).toHaveLength(1)

    const scheduleCall = getMock.mock.calls.find((call) => call[0] === '/api/schedules')
    expect(scheduleCall?.[1]?.params).toMatchObject({
      contract_no: 'HT-001',
      warning_level: 'abnormal',
      schedule_bucket: 'risk',
      date_from: '2026-03-01',
      date_to: '2026-03-31',
    })
  })

  it('redirects to login when table feedback state is auth', async () => {
    const wrapper = await buildWrapper()
    feedbackState.value = 'auth'

    await wrapper.vm.handleTableStateAction()

    expect(pushMock).toHaveBeenCalledWith({
      name: 'AdminAuth',
      query: { redirect: '/schedules' },
    })
  })

  it('disables the run action when the session lacks schedule.manage', async () => {
    const wrapper = await buildWrapper()
    getAuthSessionStateMock.mockReturnValue({
      authenticated: true,
      roleCodes: [],
      permissionCodes: ['schedule.view'],
    })

    expect(
      wrapper.vm.getRunActionState({
        order_line_id: 101,
        schedule_status: 'schedulable',
      }).disabled,
    ).toBe(true)
    expect(
      wrapper.vm.getRunActionState({
        order_line_id: 101,
        schedule_status: 'schedulable',
      }).reason,
    ).toContain('没有执行排产的权限')
  })

  it('shows a permission error instead of redirecting to login when schedule.manage is missing', async () => {
    const wrapper = await buildWrapper()
    ensureAuthSessionMock.mockResolvedValue(false)
    getAuthSessionStateMock.mockReturnValue({
      authenticated: true,
      roleCodes: [],
      permissionCodes: ['schedule.view'],
    })

    await wrapper.vm.handleRunPartSchedule({
      order_line_id: 101,
      schedule_status: 'schedulable',
      confirmed_delivery_date: '2026-03-28',
      trigger_date: undefined,
    })

    expect(errorMessageMock).toHaveBeenCalledWith('当前账号没有执行排产的权限')
    expect(pushMock).not.toHaveBeenCalled()
    expect(postMock).not.toHaveBeenCalled()
  })

  it('redirects to login when schedule action is attempted without an authenticated session', async () => {
    const wrapper = await buildWrapper()
    ensureAuthSessionMock.mockResolvedValue(false)
    getAuthSessionStateMock.mockReturnValue({
      authenticated: false,
      roleCodes: [],
      permissionCodes: [],
    })

    await wrapper.vm.handleRunPartSchedule({
      order_line_id: 101,
      schedule_status: 'schedulable',
      confirmed_delivery_date: '2026-03-28',
      trigger_date: undefined,
    })

    expect(pushMock).toHaveBeenCalledWith({
      name: 'AdminAuth',
      query: { redirect: '/schedules' },
    })
    expect(postMock).not.toHaveBeenCalled()
  })

  it('shows validation alert when running part schedule fails on blocking items', async () => {
    const wrapper = await buildWrapper()

    await wrapper.vm.handleRunPartSchedule({
      order_line_id: 101,
      schedule_status: 'schedulable',
      confirmed_delivery_date: '2026-03-28',
      trigger_date: undefined,
    })

    expect(postMock).toHaveBeenCalledWith('/api/admin/schedule/run-one-part', {
      order_line_id: 101,
    })
    expect(alertMock).toHaveBeenCalledWith(
      expect.anything(),
      '零件排产前置校验未通过',
      expect.objectContaining({ confirmButtonText: '我知道了' }),
    )
    const alertVNode = alertMock.mock.calls[0]?.[0] as { children?: string }
    expect(alertVNode.children).toContain('• BOM：缺少 BOM')
  })
})
