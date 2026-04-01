import { computed, nextTick, onMounted, onUnmounted, ref, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Box,
  Calendar,
  Document,
  DocumentCopy,
  PieChart,
  SetUp,
  ShoppingCart,
  TrendCharts,
  Warning,
  WarningFilled,
} from '@element-plus/icons-vue'
import { useDashboardOverview } from './useDashboardOverview'
import { useLocalTablePagination } from './useTablePagination'
import { applyLocalSort, getTableSortColumnProps, useTableSort } from './useTableSort'
import { SCHEDULE_STATUS_MAP } from '../constants/enums'
import type {
  DashboardBusinessGroupSummaryItem,
  DashboardMonthCountItem,
  DashboardSummaryCountItem,
  DashboardTrendPoint,
  MachineScheduleItem,
} from '../types/apiModels'
import { cleanParams, getStatusColor } from '../utils/format'
import type {
  BarChartOptions,
  DashboardChartInstance,
  DonutChartOptions,
  LineChartOptions,
} from '../utils/dashboardChartOptions'
import type { StatusBadgeTone } from '../utils/statusPresentation'
import { measureAsync, recordPerfPoint } from '../utils/performance'

export type DashboardMode = 'planner' | 'management'
export type DashboardTrendDimension = 'day' | 'week' | 'month'
export type DashboardRhythmDimension = 'day' | 'month'

export interface DashboardModeOption {
  value: DashboardMode
  label: string
  description: string
}

export interface DashboardCard {
  key: string
  title: string
  value: number | string
  description: string
  footnote: string
  tone: StatusBadgeTone
  icon: Component
}

export interface DashboardSignalCard {
  key: string
  title: string
  value: string
  description: string
  tone: StatusBadgeTone
  action?: () => void
  actionLabel?: string
}

export interface DashboardChartAction {
  key: string
  label: string
  active?: boolean
}

export interface DashboardSignalStat {
  label: string
  value: string
  tone?: StatusBadgeTone
}

interface DashboardChartPanelBase {
  key: string
  title: string
  description: string
  tone: StatusBadgeTone
  icon: Component
  span: 4 | 6 | 8 | 12
  hasData: boolean
  emptyText: string
  stats: DashboardSignalStat[]
  actions?: DashboardChartAction[]
}

interface DashboardLineChartPanel extends DashboardChartPanelBase {
  kind: 'line'
  options: LineChartOptions
}

interface DashboardDonutChartPanel extends DashboardChartPanelBase {
  kind: 'donut'
  options: DonutChartOptions
}

interface DashboardBarChartPanel extends DashboardChartPanelBase {
  kind: 'bar' | 'bar-horizontal'
  options: BarChartOptions
}

export type DashboardChartPanel = DashboardLineChartPanel | DashboardDonutChartPanel | DashboardBarChartPanel

const DASHBOARD_MODE_STORAGE_KEY = 'dashboard-mode-preference'

const getInitialDashboardMode = (): DashboardMode => {
  if (typeof window === 'undefined') return 'planner'
  const savedMode = window.localStorage.getItem(DASHBOARD_MODE_STORAGE_KEY)
  return savedMode === 'management' ? 'management' : 'planner'
}

export const useScheduleDashboardPage = () => {
  const sortableColumnProps = getTableSortColumnProps()
  const router = useRouter()
  const route = useRoute()
  const {
    dashboardOverview,
    dashboardOverviewState,
    dashboardOverviewMessage,
    isDashboardOverviewLoading,
    isDashboardOverviewReady,
    loadDashboardOverview,
  } = useDashboardOverview()

  const chartElements = new Map<string, HTMLElement>()
  const chartInstances = new Map<string, DashboardChartInstance>()
  let chartModulePromise: Promise<typeof import('../utils/dashboardChartOptions')> | null = null

  const dashboardMode = ref<DashboardMode>(getInitialDashboardMode())
  const plannerTrendDimension = ref<DashboardTrendDimension>('day')
  const managementRhythmDimension = ref<DashboardRhythmDimension>('month')
  const {
    sortField: tableSortField,
    sortOrder: tableSortOrder,
    handleSortChange: handleTableSortChangeBase,
  } = useTableSort({ sortField: 'confirmed_delivery_date', sortOrder: 'asc' })

  const modeOptions: DashboardModeOption[] = [
    {
      value: 'planner',
      label: '计划',
      description: '聚焦交付窗口、交付风险和执行优先级。',
    },
    {
      value: 'management',
      label: '管理',
      description: '聚焦覆盖率、结构分布和异常订单池。',
    },
  ]

  const currentModeMeta = computed(
    () => modeOptions.find((item) => item.value === dashboardMode.value) || modeOptions[0],
  )

  const today = new Date()
  const todayKey = formatDateKey(today)
  const riskRangeEndKey = formatDateKey(addDays(today, 30))
  const todayLabel = todayKey

  const loadChartModule = () => {
    chartModulePromise ||= import('../utils/dashboardChartOptions')
    return chartModulePromise
  }

  const riskOrders = computed(() =>
    applyLocalSort(dashboardOverview.value?.delivery_risk_orders || [], {
      sortField: tableSortField.value,
      sortOrder: tableSortOrder.value,
    }),
  )

  const abnormalMachineOrders = computed(() =>
    applyLocalSort(dashboardOverview.value?.abnormal_machine_orders || [], {
      sortField: tableSortField.value,
      sortOrder: tableSortOrder.value,
    }),
  )

  const overdueRiskOrders = computed(() =>
    riskOrders.value.filter((item) => {
      if (!item.confirmed_delivery_date) return false
      return getDiffDays(todayKey, item.confirmed_delivery_date) <= 0
    }),
  )

  const focusRiskOrders = computed(() =>
    riskOrders.value.filter((item) => {
      if (!item.confirmed_delivery_date) return false
      const diffDays = getDiffDays(todayKey, item.confirmed_delivery_date)
      return diffDays > 0 && diffDays <= 7
    }),
  )

  const statusChartData = computed(() =>
    (dashboardOverview.value?.machine_summary.status_counts || []).map((item: DashboardSummaryCountItem) => ({
      name: SCHEDULE_STATUS_MAP[item.key]?.label || item.key,
      value: item.count,
      itemStyle: { color: getStatusColor(item.key) },
    })),
  )

  const monthCounts = computed(() =>
    (dashboardOverview.value?.machine_summary.planned_end_month_counts || [])
      .slice()
      .sort((a: DashboardMonthCountItem, b: DashboardMonthCountItem) => a.key.localeCompare(b.key)),
  )

  const rhythmDayCounts = computed(() =>
    (dashboardOverview.value?.machine_summary.planned_end_day_counts || [])
      .slice()
      .sort((a: DashboardSummaryCountItem, b: DashboardSummaryCountItem) => a.key.localeCompare(b.key)),
  )

  const rhythmChartData = computed(() =>
    managementRhythmDimension.value === 'day' ? rhythmDayCounts.value : monthCounts.value,
  )

  const plannerTrendPoints = computed<DashboardTrendPoint[]>(() => {
    const trends = dashboardOverview.value?.delivery_trends
    if (!trends) return []
    return trends[plannerTrendDimension.value] || []
  })

  const businessGroupSummary = computed<DashboardBusinessGroupSummaryItem[]>(() =>
    dashboardOverview.value?.business_group_summary || [],
  )

  const plannerCards = computed<DashboardCard[]>(() => {
    const overview = dashboardOverview.value
    if (!overview) return []
    return [
      {
        key: 'today-delivery',
        title: '今日交付',
        value: overview.today_summary.delivery_count,
        description: '今天确认交期内的订单数量。',
        footnote: `${overview.today_summary.abnormal_count} 单带异常标识`,
        tone: 'success',
        icon: Calendar,
      },
      {
        key: 'week-delivery',
        title: '本周交付',
        value: overview.week_summary.delivery_count,
        description: '本周交付窗口内的交付任务量。',
        footnote: `${overview.week_summary.unscheduled_count} 单仍未排产`,
        tone: 'primary',
        icon: Document,
      },
      {
        key: 'month-delivery',
        title: '本月交付',
        value: overview.month_summary.delivery_count,
        description: '本月范围内需要完成的交付总量。',
        footnote: `${overview.month_summary.abnormal_count} 单需盯盘`,
        tone: 'blue',
        icon: TrendCharts,
      },
      {
        key: 'unscheduled-orders',
        title: '待排产订单',
        value: overview.machine_summary.unscheduled_orders,
        description: '当前仍未进入整机排产的订单。',
        footnote: '优先压缩临近交付窗口的未排产积压',
        tone: 'warning',
        icon: SetUp,
      },
      {
        key: 'delivery-risk',
        title: '30天交付风险',
        value: riskOrders.value.length,
        description: '沿用现有风险池口径的未来 30 天风险订单。',
        footnote: `${overdueRiskOrders.value.length} 单已进入逾期窗口`,
        tone: 'danger',
        icon: WarningFilled,
      },
      {
        key: 'overdue-orders',
        title: '逾期订单',
        value: overdueRiskOrders.value.length,
        description: '风险池内确认交期已到今天或更早的订单。',
        footnote: '需要优先核查当前排产和交付状态',
        tone: 'danger',
        icon: Warning,
      },
      {
        key: 'focus-orders',
        title: '重点关注订单',
        value: focusRiskOrders.value.length,
        description: '风险池内未来 7 天要优先推进的订单。',
        footnote: '默认不含已逾期订单',
        tone: 'orange',
        icon: DocumentCopy,
      },
    ]
  })

  const managementCards = computed<DashboardCard[]>(() => {
    const overview = dashboardOverview.value
    if (!overview) return []
    return [
      {
        key: 'machine-total',
        title: '整机排产总量',
        value: overview.machine_summary.total_orders,
        description: '当前纳入 Dashboard 的整机订单总数。',
        footnote: `${overview.machine_summary.scheduled_orders} 单已排产`,
        tone: 'primary',
        icon: ShoppingCart,
      },
      {
        key: 'machine-scheduled',
        title: '已排产订单',
        value: overview.machine_summary.scheduled_orders,
        description: '已进入整机排产的订单数量。',
        footnote: `${formatPercent(overview.machine_summary.scheduled_orders, overview.machine_summary.total_orders)} 覆盖率`,
        tone: 'success',
        icon: Calendar,
      },
      {
        key: 'machine-abnormal',
        title: '异常整机订单',
        value: overview.machine_summary.abnormal_orders,
        description: '当前带异常标识的整机订单数量。',
        footnote: `${abnormalMachineOrders.value.length} 单进入异常池`,
        tone: 'danger',
        icon: WarningFilled,
      },
      {
        key: 'coverage-rate',
        title: '排产覆盖率',
        value: formatPercent(overview.machine_summary.scheduled_orders, overview.machine_summary.total_orders),
        description: '已排产订单占整机订单总量的比例。',
        footnote: `${overview.machine_summary.scheduled_orders}/${overview.machine_summary.total_orders}`,
        tone: 'success',
        icon: PieChart,
      },
      {
        key: 'abnormal-rate',
        title: '订单异常率',
        value: formatPercent(overview.machine_summary.abnormal_orders, overview.machine_summary.total_orders),
        description: '异常整机订单占整机总量的比例。',
        footnote: `${overview.machine_summary.abnormal_orders} 单异常整机`,
        tone: 'danger',
        icon: Warning,
      },
      {
        key: 'part-total',
        title: '零件排产总量',
        value: overview.part_summary.total_parts,
        description: '当前零件排产任务的总体规模。',
        footnote: `${overview.part_summary.top_assemblies.length} 个部装进入统计`,
        tone: 'cyan',
        icon: Box,
      },
      {
        key: 'part-abnormal-rate',
        title: '零件异常率',
        value: formatPercent(overview.part_summary.abnormal_parts, overview.part_summary.total_parts),
        description: '异常零件任务占零件总量的比例。',
        footnote: `${overview.part_summary.abnormal_parts} 条异常零件`,
        tone: 'warning',
        icon: DocumentCopy,
      },
    ]
  })

  const cards = computed(() => (dashboardMode.value === 'planner' ? plannerCards.value : managementCards.value))

  const chartPanels = computed<DashboardChartPanel[]>(() => {
    const overview = dashboardOverview.value
    if (!overview) return []

    if (dashboardMode.value === 'planner') {
      return [
        {
          key: 'planner-delivery-trend',
          kind: 'line',
          title: '排产交付趋势',
          description: '按日期观察计划开工与确认交付的节奏变化。',
          tone: 'success',
          icon: TrendCharts,
          span: 8,
          hasData: plannerTrendPoints.value.length > 0,
          emptyText: '暂无排产交付趋势数据',
          actions: [
            { key: 'day', label: '日', active: plannerTrendDimension.value === 'day' },
            { key: 'week', label: '周', active: plannerTrendDimension.value === 'week' },
            { key: 'month', label: '月', active: plannerTrendDimension.value === 'month' },
          ],
          stats: [
            { label: '风险订单', value: String(riskOrders.value.length), tone: 'danger' },
            { label: '逾期订单', value: String(overdueRiskOrders.value.length), tone: 'danger' },
            { label: '重点关注', value: String(focusRiskOrders.value.length), tone: 'warning' },
          ],
          options: {
            categories: plannerTrendPoints.value.map((item) => item.label),
            series: [
              {
                name: '排产数量',
                data: plannerTrendPoints.value.map((item) => item.scheduled_count),
                color: '#82d695',
              },
              {
                name: '交付数量',
                data: plannerTrendPoints.value.map((item) => item.delivery_count),
                color: '#7fdfff',
              },
            ],
          },
        },
        {
          key: 'planner-status',
          kind: 'donut',
          title: '整机排产状态',
          description: '按排产状态占比观察当前整机订单结构。',
          tone: 'primary',
          icon: PieChart,
          span: 4,
          hasData: statusChartData.value.length > 0,
          emptyText: '暂无整机状态分布',
          stats: [
            { label: '总订单', value: String(overview.machine_summary.total_orders), tone: 'primary' },
            { label: '已排产', value: String(overview.machine_summary.scheduled_orders), tone: 'success' },
            { label: '待排产', value: String(overview.machine_summary.unscheduled_orders), tone: 'warning' },
          ],
          options: {
            data: statusChartData.value,
            centerLabel: `${overview.machine_summary.total_orders}\n订单`,
          },
        },
      ]
    }

    return [
      {
        key: 'management-rhythm',
        kind: 'line',
        title: '计划完工节奏',
        description: '按计划完工日期观察整机订单的节奏分布。',
        tone: 'cyan',
        icon: TrendCharts,
        span: 12,
        hasData: rhythmChartData.value.length > 0,
        emptyText: '暂无计划完工节奏数据',
        actions: [
          { key: 'day', label: '日', active: managementRhythmDimension.value === 'day' },
          { key: 'month', label: '月', active: managementRhythmDimension.value === 'month' },
        ],
        stats: [
          { label: managementRhythmDimension.value === 'day' ? '天数跨度' : '月份跨度', value: String(rhythmChartData.value.length), tone: 'cyan' },
          { label: '整机总量', value: String(overview.machine_summary.total_orders), tone: 'primary' },
          { label: '异常整机', value: String(overview.machine_summary.abnormal_orders), tone: 'danger' },
        ],
        options: {
          categories: rhythmChartData.value.map((item) => managementRhythmDimension.value === 'day' ? item.key.slice(5) : item.key),
          showArea: managementRhythmDimension.value === 'month',
          series: [
            {
              name: '计划完工订单',
              data: rhythmChartData.value.map((item) => item.count),
              color: '#6ef6ff',
              ...(managementRhythmDimension.value === 'month' ? { areaColor: '#6ef6ff' } : {}),
            },
          ],
        },
      },
      {
        key: 'management-status',
        kind: 'donut',
        title: '整机状态分布',
        description: '从管理视角看整机订单当前的排产结构。',
        tone: 'success',
        icon: PieChart,
        span: 6,
        hasData: statusChartData.value.length > 0,
        emptyText: '暂无整机状态分布',
        stats: [
          { label: '覆盖率', value: formatPercent(overview.machine_summary.scheduled_orders, overview.machine_summary.total_orders), tone: 'success' },
          { label: '待排产', value: String(overview.machine_summary.unscheduled_orders), tone: 'warning' },
          { label: '异常整机', value: String(overview.machine_summary.abnormal_orders), tone: 'danger' },
        ],
        options: {
          data: statusChartData.value,
          centerLabel: `${formatPercent(overview.machine_summary.scheduled_orders, overview.machine_summary.total_orders)}\n覆盖`,
        },
      },
      {
        key: 'management-business-group',
        kind: 'bar',
        title: '事业群订单数据',
        description: '并列展示各事业群的订单数量和订单金额。',
        tone: 'blue',
        icon: Document,
        span: 6,
        hasData: businessGroupSummary.value.length > 0,
        emptyText: '暂无事业群订单数据',
        stats: [
          { label: '事业群数', value: String(businessGroupSummary.value.length), tone: 'blue' },
          { label: '订单总量', value: String(overview.machine_summary.total_orders), tone: 'primary' },
          { label: '订单金额', value: `${formatAmountWan(toAmountWan(sumBusinessGroupAmount(businessGroupSummary.value)))} 万`, tone: 'cyan' },
        ],
        options: {
          categories: businessGroupSummary.value.map((item) => item.business_group),
          dualAxis: true,
          series: [
            {
              name: '订单数量',
              data: businessGroupSummary.value.map((item) => item.order_count),
              color: '#82d695',
            },
            {
              name: '订单金额(万元)',
              data: businessGroupSummary.value.map((item) => toAmountWan(item.total_amount)),
              color: '#7fdfff',
            },
          ],
        },
      },
    ]
  })

  const activeTableRows = computed(() =>
    dashboardMode.value === 'planner' ? riskOrders.value : abnormalMachineOrders.value,
  )

  const {
    pageNo: activeTablePageNo,
    pageSize: activeTablePageSize,
    pageSizes: activeTablePageSizes,
    total: activeTableTotal,
    pagedData: pagedActiveTableRows,
    resetPagination: resetActiveTablePagination,
  } = useLocalTablePagination(() => activeTableRows.value)

  const activeTableTitle = computed(() =>
    dashboardMode.value === 'planner' ? '未来 30 天交付风险订单' : '异常整机订单池',
  )

  const activeTableDescription = computed(() =>
    dashboardMode.value === 'planner'
      ? '按确认交期优先展示未来 30 天内最需要盯盘的交付风险订单。'
      : '集中展示当前带异常标识的整机订单，便于管理侧统一排查。',
  )

  const activeTableEmptyText = computed(() =>
    dashboardMode.value === 'planner' ? '未来 30 天暂无交付风险订单' : '当前暂无异常整机订单',
  )

  const dashboardStateTitle = computed(() => {
    if (dashboardOverviewState.value === 'loading') return '总览加载中'
    if (dashboardOverviewState.value === 'empty') return '暂无总览数据'
    if (dashboardOverviewState.value === 'auth') return '登录状态已失效'
    return '总览加载失败'
  })

  const dashboardStateBodyText = computed(() => {
    if (dashboardOverviewState.value === 'loading') {
      return '正在读取排产总览，请稍候。'
    }
    if (dashboardOverviewState.value === 'empty') {
      return '排产总览接口已返回成功，但当前暂时没有可展示的整机或零件统计数据。'
    }
    return dashboardOverviewMessage.value || '排产总览加载失败，请稍后重试。'
  })

  const showDashboardRetryAction = computed(
    () => dashboardOverviewState.value === 'empty' || dashboardOverviewState.value === 'error',
  )
  const showDashboardLoginAction = computed(() => dashboardOverviewState.value === 'auth')

  const setChartRef = (key: string, element: Element | null) => {
    if (!element) {
      chartElements.delete(key)
      const chart = chartInstances.get(key)
      chart?.dispose()
      chartInstances.delete(key)
      return
    }
    chartElements.set(key, element as HTMLElement)
  }

  const disposeCharts = (keys?: Iterable<string>) => {
    if (!keys) {
      chartInstances.forEach((chart) => chart.dispose())
      chartInstances.clear()
      return
    }
    Array.from(keys).forEach((key) => {
      const chart = chartInstances.get(key)
      chart?.dispose()
      chartInstances.delete(key)
    })
  }

  const renderCharts = async () => {
    if (!isDashboardOverviewReady.value) {
      disposeCharts()
      return
    }

    const activePanels = chartPanels.value
    const activeKeys = new Set(activePanels.filter((panel) => panel.hasData).map((panel) => panel.key))
    const staleKeys = Array.from(chartInstances.keys()).filter((key) => !activeKeys.has(key))
    if (staleKeys.length > 0) {
      disposeCharts(staleKeys)
    }

    const chartStart = performance.now()
    await nextTick()
    const chartModule = await loadChartModule()

    activePanels.forEach((panel) => {
      if (!panel.hasData) {
        const existingChart = chartInstances.get(panel.key)
        existingChart?.dispose()
        chartInstances.delete(panel.key)
        return
      }
      const element = chartElements.get(panel.key)
      if (!element) return
      const currentChart = chartInstances.get(panel.key)

      if (panel.kind === 'donut') {
        chartInstances.set(panel.key, chartModule.renderDonutChart(element, panel.options, currentChart))
        return
      }
      if (panel.kind === 'bar') {
        chartInstances.set(panel.key, chartModule.renderVerticalBarChart(element, panel.options, currentChart))
        return
      }
      if (panel.kind === 'bar-horizontal') {
        chartInstances.set(panel.key, chartModule.renderHorizontalBarChart(element, panel.options, currentChart))
        return
      }
      chartInstances.set(panel.key, chartModule.renderLineChart(element, panel.options, currentChart))
    })

    recordPerfPoint('dashboard', 'renderPerspectiveCharts', performance.now() - chartStart, 'success', {
      mode: dashboardMode.value,
      chartCount: activePanels.filter((panel) => panel.hasData).length,
    })
  }

  const initializeDashboardOverview = async () => {
    await loadDashboardOverview()
    await renderCharts()
  }

  const reloadDashboardOverview = async () => {
    await measureAsync('dashboard', 'reloadOverview', async () => {
      await loadDashboardOverview({ forceRefresh: true })
    })
    await renderCharts()
  }

  const handleResize = () => {
    chartInstances.forEach((chart) => chart.resize())
  }

  const handleGoToLogin = () => {
    router.push({
      name: 'AdminAuth',
      query: { redirect: route.fullPath },
    })
  }

  const handleViewAllActiveTable = () => {
    if (dashboardMode.value === 'planner') {
      goToSchedules({ schedule_bucket: 'risk', date_from: todayKey, date_to: riskRangeEndKey })
      return
    }
    goToSchedules({ warning_level: 'abnormal' })
  }

  const goToSchedules = (query: Record<string, string> = {}) => {
    router.push({ path: '/schedules', query: cleanParams(query) })
  }

  const goToDetail = (row: MachineScheduleItem) => {
    router.push(`/schedules/${row.order_line_id}`)
  }

  const handleTableSortChange = (sort: { prop?: string; order?: 'ascending' | 'descending' | null }) => {
    handleTableSortChangeBase(sort)
  }

  const triggerPanelAction = (panelKey: string, actionKey: string) => {
    if (panelKey === 'planner-delivery-trend' && isTrendDimension(actionKey)) {
      plannerTrendDimension.value = actionKey
    }
    if (panelKey === 'management-rhythm' && isRhythmDimension(actionKey)) {
      managementRhythmDimension.value = actionKey
    }
  }

  watch(dashboardMode, () => {
    resetActiveTablePagination()
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(DASHBOARD_MODE_STORAGE_KEY, dashboardMode.value)
    }
    if (isDashboardOverviewReady.value) {
      void renderCharts()
    }
  })

  watch(plannerTrendDimension, () => {
    if (dashboardMode.value === 'planner' && isDashboardOverviewReady.value) {
      void renderCharts()
    }
  })

  watch(managementRhythmDimension, () => {
    if (dashboardMode.value === 'management' && isDashboardOverviewReady.value) {
      void renderCharts()
    }
  })

  watch(
    () => dashboardOverview.value,
    () => {
      resetActiveTablePagination()
      if (isDashboardOverviewReady.value) {
        void renderCharts()
      }
    },
  )

  watch(dashboardOverviewState, (state) => {
    if (state !== 'ready') {
      disposeCharts()
    }
  })

  onMounted(() => {
    void initializeDashboardOverview()
    window.addEventListener('resize', handleResize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    disposeCharts()
  })

  return {
    activeTableDescription,
    activeTableEmptyText,
    activeTablePageNo,
    activeTablePageSize,
    activeTablePageSizes,
    activeTableTitle,
    activeTableTotal,
    cards,
    chartPanels,
    currentModeDescription: computed(() => currentModeMeta.value.description),
    dashboardMode,
    dashboardStateBodyText,
    dashboardStateTitle,
    formatQuantity,
    goToDetail,
    handleGoToLogin,
    handleTableSortChange,
    handleViewAllActiveTable,
    isDashboardOverviewLoading,
    isDashboardOverviewReady,
    modeOptions,
    pagedActiveTableRows,
    reloadDashboardOverview,
    setChartRef,
    showDashboardLoginAction,
    showDashboardRetryAction,
    sortableColumnProps,
    todayLabel,
    triggerPanelAction,
  }
}

function isTrendDimension(value: string): value is DashboardTrendDimension {
  return value === 'day' || value === 'week' || value === 'month'
}

function isRhythmDimension(value: string): value is DashboardRhythmDimension {
  return value === 'day' || value === 'month'
}

function formatDateKey(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addDays(value: Date, days: number) {
  const next = new Date(value)
  next.setDate(next.getDate() + days)
  return next
}

function formatQuantity(value?: number | string | null) {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return String(value)
  if (Number.isInteger(numeric)) return String(numeric)
  return numeric.toFixed(2).replace(/\.?0+$/, '')
}

function formatPercent(value: number, total: number) {
  if (!total) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

function getDiffDays(startKey: string, endKey: string) {
  const start = Date.parse(startKey)
  const end = Date.parse(endKey)
  if (Number.isNaN(start) || Number.isNaN(end)) return 0
  return Math.floor((end - start) / (1000 * 60 * 60 * 24))
}

function toAmountWan(value?: number | string | null) {
  if (value === null || value === undefined || value === '') return 0
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return 0
  return Number((numeric / 10000).toFixed(2))
}

function formatAmountWan(value: number) {
  if (!Number.isFinite(value)) return '0'
  if (Number.isInteger(value)) return String(value)
  return value.toFixed(2).replace(/\.?0+$/, '')
}

function sumBusinessGroupAmount(items: DashboardBusinessGroupSummaryItem[]) {
  return items.reduce((total, item) => total + Number(item.total_amount || 0), 0)
}
