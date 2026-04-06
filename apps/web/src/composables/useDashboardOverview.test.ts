import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { DashboardOverviewResponse } from '../types/apiModels'

const getMock = vi.fn()

vi.mock('../utils/httpClient', () => ({
  default: {
    get: getMock,
  },
}))

vi.mock('../utils/requestCache', () => ({
  getCachedAsync: vi.fn(async (_key: string, _ttl: number, loader: () => Promise<unknown>) => loader()),
  clearCachedRequest: vi.fn(),
}))

const createEmptyOverview = (): DashboardOverviewResponse => ({
  machine_summary: {
    total_orders: 0,
    scheduled_orders: 0,
    unscheduled_orders: 0,
    abnormal_orders: 0,
    status_counts: [],
    planned_end_month_counts: [],
    warning_orders: [],
  },
  part_summary: {
    total_parts: 0,
    abnormal_parts: 0,
    warning_counts: [],
    top_assemblies: [],
  },
  today_summary: { delivery_count: 0, unscheduled_count: 0, abnormal_count: 0 },
  week_summary: { delivery_count: 0, unscheduled_count: 0, abnormal_count: 0 },
  month_summary: { delivery_count: 0, unscheduled_count: 0, abnormal_count: 0 },
  delivery_trends: { day: [], week: [], month: [] },
  business_group_summary: [],
  abnormal_machine_orders: [],
  delivery_risk_orders: [],
})

const createPopulatedOverview = (): DashboardOverviewResponse => ({
  ...createEmptyOverview(),
  machine_summary: {
    total_orders: 100,
    scheduled_orders: 80,
    unscheduled_orders: 20,
    abnormal_orders: 5,
    status_counts: [{ key: 'scheduled', count: 80 }],
    planned_end_month_counts: [],
    warning_orders: [],
  },
  part_summary: {
    total_parts: 50,
    abnormal_parts: 3,
    warning_counts: [],
    top_assemblies: [],
  },
  today_summary: { delivery_count: 5, unscheduled_count: 2, abnormal_count: 1 },
  week_summary: { delivery_count: 20, unscheduled_count: 5, abnormal_count: 3 },
  month_summary: { delivery_count: 60, unscheduled_count: 10, abnormal_count: 5 },
})

describe('useDashboardOverview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initial state is loading', async () => {
    const { useDashboardOverview } = await import('./useDashboardOverview')
    const {
      dashboardOverview,
      dashboardOverviewState,
      isDashboardOverviewLoading,
      isDashboardOverviewReady,
    } = useDashboardOverview()

    expect(dashboardOverview.value).toBeNull()
    expect(dashboardOverviewState.value).toBe('loading')
    expect(isDashboardOverviewLoading.value).toBe(true)
    expect(isDashboardOverviewReady.value).toBe(false)
  })

  it('transitions to ready state on successful load', async () => {
    getMock.mockResolvedValueOnce(createPopulatedOverview())

    const { useDashboardOverview } = await import('./useDashboardOverview')
    const { dashboardOverview, dashboardOverviewState, loadDashboardOverview } = useDashboardOverview()

    await loadDashboardOverview()

    expect(dashboardOverviewState.value).toBe('ready')
    expect(dashboardOverview.value).not.toBeNull()
    expect(dashboardOverview.value!.machine_summary.total_orders).toBe(100)
  })

  it('transitions to empty state when overview has no data', async () => {
    getMock.mockResolvedValueOnce(createEmptyOverview())

    const { useDashboardOverview } = await import('./useDashboardOverview')
    const { dashboardOverviewState, dashboardOverviewMessage, loadDashboardOverview } = useDashboardOverview()

    await loadDashboardOverview()

    expect(dashboardOverviewState.value).toBe('empty')
    expect(dashboardOverviewMessage.value).toContain('暂时没有可展示')
  })

  it('transitions to auth state on 401 error', async () => {
    const error = Object.assign(new Error('Unauthorized'), { status: 401 })
    getMock.mockRejectedValueOnce(error)

    const { useDashboardOverview } = await import('./useDashboardOverview')
    const { dashboardOverviewState, dashboardOverviewMessage, loadDashboardOverview } = useDashboardOverview()

    await loadDashboardOverview()

    expect(dashboardOverviewState.value).toBe('auth')
    expect(dashboardOverviewMessage.value).toContain('登录状态已失效')
  })

  it('transitions to error state on generic error', async () => {
    getMock.mockRejectedValueOnce(new Error('服务端异常'))

    const { useDashboardOverview } = await import('./useDashboardOverview')
    const { dashboardOverviewState, dashboardOverviewMessage, loadDashboardOverview } = useDashboardOverview()

    await loadDashboardOverview()

    expect(dashboardOverviewState.value).toBe('error')
    expect(dashboardOverviewMessage.value).toContain('服务端异常')
  })

  it('forceRefresh clears cache before loading', async () => {
    const { clearCachedRequest } = await import('../utils/requestCache')
    getMock.mockResolvedValueOnce(createPopulatedOverview())

    const { useDashboardOverview } = await import('./useDashboardOverview')
    const { loadDashboardOverview } = useDashboardOverview()

    await loadDashboardOverview({ forceRefresh: true })

    expect(clearCachedRequest).toHaveBeenCalledWith('dashboard:overview')
  })
})

describe('isDashboardOverviewEmpty', () => {
  it('returns true for empty overview', async () => {
    const { isDashboardOverviewEmpty } = await import('./useDashboardOverview')
    expect(isDashboardOverviewEmpty(createEmptyOverview())).toBe(true)
  })

  it('returns false when there are orders', async () => {
    const { isDashboardOverviewEmpty } = await import('./useDashboardOverview')
    expect(isDashboardOverviewEmpty(createPopulatedOverview())).toBe(false)
  })
})
