import { computed, ref } from 'vue'
import type { DashboardOverviewResponse } from '../types/apiModels'
import request from '../utils/httpClient'
import { clearCachedRequest, getCachedAsync } from '../utils/requestCache'

export type DashboardOverviewState = 'loading' | 'ready' | 'empty' | 'error' | 'auth'

const DASHBOARD_OVERVIEW_URL = '/api/dashboard/overview'
const DASHBOARD_OVERVIEW_CACHE_KEY = 'dashboard:overview'
const DASHBOARD_OVERVIEW_CACHE_TTL_MS = 60 * 1000

const hasPositiveTimeSummary = (value?: {
  delivery_count?: number
  unscheduled_count?: number
  abnormal_count?: number
} | null) =>
  Boolean(
    (value?.delivery_count ?? 0) > 0 ||
      (value?.unscheduled_count ?? 0) > 0 ||
      (value?.abnormal_count ?? 0) > 0,
  )

export const isDashboardOverviewEmpty = (overview: DashboardOverviewResponse) =>
  overview.machine_summary.total_orders <= 0 &&
  overview.part_summary.total_parts <= 0 &&
  !hasPositiveTimeSummary(overview.today_summary) &&
  !hasPositiveTimeSummary(overview.week_summary) &&
  !hasPositiveTimeSummary(overview.month_summary) &&
  overview.machine_summary.warning_orders.length === 0 &&
  overview.delivery_risk_orders.length === 0

const resolveDashboardStateMessage = (
  state: Exclude<DashboardOverviewState, 'loading' | 'ready'>,
  error: unknown,
) => {
  const status = typeof error === 'object' && error && 'status' in error ? (error as { status?: number }).status : undefined
  const message = error instanceof Error ? error.message.trim() : ''

  if (state === 'auth') {
    return '登录状态已失效，请重新登录后再查看排产总览。'
  }

  if (status === 404) {
    return '排产总览接口暂不可用，请确认后端已提供 /api/dashboard/overview。'
  }

  if (message) {
    return message
  }

  return '排产总览加载失败，请稍后重试。'
}

export const useDashboardOverview = () => {
  const overview = ref<DashboardOverviewResponse | null>(null)
  const state = ref<DashboardOverviewState>('loading')
  const message = ref('正在读取排产总览，请稍候...')

  const isLoading = computed(() => state.value === 'loading')
  const isReady = computed(() => state.value === 'ready')

  const loadOverview = async (options?: { forceRefresh?: boolean }) => {
    state.value = 'loading'
    message.value = '正在读取排产总览，请稍候...'

    try {
      if (options?.forceRefresh) {
        clearCachedRequest(DASHBOARD_OVERVIEW_CACHE_KEY)
      }
      const data = await getCachedAsync(DASHBOARD_OVERVIEW_CACHE_KEY, DASHBOARD_OVERVIEW_CACHE_TTL_MS, () =>
        request.get<DashboardOverviewResponse>(DASHBOARD_OVERVIEW_URL, {
          silentError: true,
        }),
      )
      overview.value = data
      if (isDashboardOverviewEmpty(data)) {
        state.value = 'empty'
        message.value = '当前排产总览已返回成功，但暂时没有可展示的整机或零件统计数据。'
        return
      }
      state.value = 'ready'
      message.value = ''
    } catch (error) {
      overview.value = null
      const status = typeof error === 'object' && error && 'status' in error ? (error as { status?: number }).status : undefined
      state.value = status === 401 || status === 403 ? 'auth' : 'error'
      message.value = resolveDashboardStateMessage(state.value, error)
    }
  }

  return {
    dashboardOverview: overview,
    dashboardOverviewState: state,
    dashboardOverviewMessage: message,
    isDashboardOverviewLoading: isLoading,
    isDashboardOverviewReady: isReady,
    loadDashboardOverview: loadOverview,
  }
}
