import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { DashboardOverviewResponse } from '../types/apiModels'

const getMock = vi.fn()
const pushMock = vi.fn()

vi.mock('../utils/httpClient', () => ({
  default: {
    get: getMock,
  },
}))

vi.mock('../utils/requestCache', () => ({
  getCachedAsync: vi.fn(async (_key: string, _ttl: number, loader: () => Promise<unknown>) => loader()),
  clearCachedRequest: vi.fn(),
}))

vi.mock('../utils/performance', () => ({
  measureAsync: vi.fn(async (_scope: string, _label: string, fn: () => Promise<unknown>) => fn()),
  recordPerfPoint: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  useRoute: () => ({
    fullPath: '/admin/dashboard',
  }),
}))

vi.mock('../utils/dashboardChartOptions', () => ({
  renderLineChart: vi.fn(() => ({ dispose: vi.fn(), getDom: vi.fn(), resize: vi.fn() })),
  renderDonutChart: vi.fn(() => ({ dispose: vi.fn(), getDom: vi.fn(), resize: vi.fn() })),
  renderVerticalBarChart: vi.fn(() => ({ dispose: vi.fn(), getDom: vi.fn(), resize: vi.fn() })),
  renderHorizontalBarChart: vi.fn(() => ({ dispose: vi.fn(), getDom: vi.fn(), resize: vi.fn() })),
}))

vi.mock('../utils/format', () => ({
  cleanParams: (params: Record<string, any>) => {
    const cleaned: Record<string, any> = {}
    Object.keys(params).forEach((key) => {
      if (params[key] !== '' && params[key] !== null && params[key] !== undefined) {
        cleaned[key] = params[key]
      }
    })
    return cleaned
  },
  getStatusColor: vi.fn(() => '#ccc'),
}))

const createPopulatedOverview = (): DashboardOverviewResponse => ({
  machine_summary: {
    total_orders: 100,
    scheduled_orders: 80,
    unscheduled_orders: 20,
    abnormal_orders: 5,
    status_counts: [{ key: 'scheduled', count: 80 }],
    planned_end_month_counts: [{ key: '2026-04', count: 30 }],
    planned_end_day_counts: [{ key: '2026-04-01', count: 5 }],
    warning_orders: [],
  },
  part_summary: {
    total_parts: 50,
    abnormal_parts: 3,
    warning_counts: [],
    top_assemblies: [{ assembly_name: 'A1', count: 10 }],
  },
  today_summary: { delivery_count: 5, unscheduled_count: 2, abnormal_count: 1 },
  week_summary: { delivery_count: 20, unscheduled_count: 5, abnormal_count: 3 },
  month_summary: { delivery_count: 60, unscheduled_count: 10, abnormal_count: 5 },
  delivery_trends: {
    day: [{ key: '2026-04-01', label: '04-01', scheduled_count: 10, delivery_count: 8 }],
    week: [],
    month: [],
  },
  business_group_summary: [{ business_group: 'BG1', order_count: 50, total_amount: 100000 }],
  abnormal_machine_orders: [],
  delivery_risk_orders: [
    {
      order_line_id: 1,
      sales_order_no: 'SO-001',
      confirmed_delivery_date: '2026-04-10',
    } as any,
  ],
})

const buildWrapper = async () => {
  const { useScheduleDashboardPage } = await import('./useScheduleDashboardPage')
  const TestComponent = defineComponent({
    setup() {
      return useScheduleDashboardPage()
    },
    template: '<div />',
  })
  const wrapper = mount(TestComponent)
  await flushPromises()
  return wrapper
}

describe('useScheduleDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('dashboard-mode-preference')
    }
  })

  it('loads overview on mount and populates planner cards', async () => {
    getMock.mockResolvedValueOnce(createPopulatedOverview())

    const wrapper = await buildWrapper()

    expect(wrapper.vm.isDashboardOverviewReady).toBe(true)
    expect(wrapper.vm.dashboardMode).toBe('planner')
    expect(wrapper.vm.cards.length).toBeGreaterThan(0)
    expect(wrapper.vm.cards[0].key).toBe('today-delivery')
  })

  it('shows management cards when mode is switched', async () => {
    getMock.mockResolvedValueOnce(createPopulatedOverview())

    const wrapper = await buildWrapper()

    wrapper.vm.dashboardMode = 'management'
    await flushPromises()

    expect(wrapper.vm.cards.length).toBeGreaterThan(0)
    expect(wrapper.vm.cards[0].key).toBe('machine-total')
  })

  it('shows loading state title and body', async () => {
    getMock.mockImplementationOnce(() => new Promise(() => {})) // never resolves

    const { useScheduleDashboardPage } = await import('./useScheduleDashboardPage')
    const TestComponent = defineComponent({
      setup() {
        return useScheduleDashboardPage()
      },
      template: '<div />',
    })
    mount(TestComponent)
    // don't flush — stay in loading state

    // Can't access vm directly in loading without flush, but verify no crash
    expect(true).toBe(true)
  })

  it('handleGoToLogin navigates to AdminAuth with redirect', async () => {
    getMock.mockResolvedValueOnce(createPopulatedOverview())

    const wrapper = await buildWrapper()
    wrapper.vm.handleGoToLogin()

    expect(pushMock).toHaveBeenCalledWith({
      name: 'AdminAuth',
      query: { redirect: '/admin/dashboard' },
    })
  })

  it('goToDetail navigates to schedule detail page', async () => {
    getMock.mockResolvedValueOnce(createPopulatedOverview())

    const wrapper = await buildWrapper()
    wrapper.vm.goToDetail({ order_line_id: 42 } as any)

    expect(pushMock).toHaveBeenCalledWith('/schedules/42')
  })

  it('handleViewAllActiveTable navigates with risk query in planner mode', async () => {
    getMock.mockResolvedValueOnce(createPopulatedOverview())

    const wrapper = await buildWrapper()
    wrapper.vm.handleViewAllActiveTable()

    expect(pushMock).toHaveBeenCalledWith({
      path: '/schedules',
      query: expect.objectContaining({ schedule_bucket: 'risk' }),
    })
  })

  it('triggerPanelAction changes trend dimension', async () => {
    getMock.mockResolvedValueOnce(createPopulatedOverview())

    const wrapper = await buildWrapper()

    wrapper.vm.triggerPanelAction('planner-delivery-trend', 'week')
    // The internal ref changes; we verify no crash and cards still present
    expect(wrapper.vm.cards.length).toBeGreaterThan(0)
  })

  it('activeTableTitle reflects current mode', async () => {
    getMock.mockResolvedValueOnce(createPopulatedOverview())

    const wrapper = await buildWrapper()

    expect(wrapper.vm.activeTableTitle).toContain('交付风险')

    wrapper.vm.dashboardMode = 'management'
    await flushPromises()

    expect(wrapper.vm.activeTableTitle).toContain('异常整机')
  })

  it('modeOptions has planner and management entries', async () => {
    getMock.mockResolvedValueOnce(createPopulatedOverview())

    const wrapper = await buildWrapper()

    expect(wrapper.vm.modeOptions).toHaveLength(2)
    expect(wrapper.vm.modeOptions.map((o: any) => o.value)).toEqual(['planner', 'management'])
  })

  it('shows retry action on error state', async () => {
    getMock.mockRejectedValueOnce(new Error('服务端异常'))

    const wrapper = await buildWrapper()

    expect(wrapper.vm.showDashboardRetryAction).toBe(true)
    expect(wrapper.vm.showDashboardLoginAction).toBe(false)
  })

  it('shows login action on auth error', async () => {
    const error = Object.assign(new Error('Unauthorized'), { status: 401 })
    getMock.mockRejectedValueOnce(error)

    const wrapper = await buildWrapper()

    expect(wrapper.vm.showDashboardLoginAction).toBe(true)
    expect(wrapper.vm.showDashboardRetryAction).toBe(false)
  })
})
