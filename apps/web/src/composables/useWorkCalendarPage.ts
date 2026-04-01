import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocalTablePagination } from './useTablePagination'
import type { TableFeedbackState } from './useTableFeedbackState'
import { applyLocalSort, useTableSort } from './useTableSort'
import request from '../utils/httpClient'
import { BUSINESS_TERMS } from '../constants/terminology'
import { measureAsync } from '../utils/performance'
import { getCachedAsync } from '../utils/requestCache'
import type {
  ScheduleCalendarDayDetailResponse,
  ScheduleCalendarDaySummary,
} from '../types/apiModels'

export interface WorkCalendarLabels {
  title: string
  subtitle: string
  delivery: string
  trigger: string
  plannedStart: string
  today: string
  backToCurrentMonth: string
  monthDelivery: string
  monthTrigger: string
  monthPlannedStart: string
  orderUnit: string
  quantityUnit: string
  deliveryShort: string
  triggerShort: string
  plannedStartShort: string
  orderShort: string
  quantityShort: string
  detailTitleSuffix: string
  deliveryOrderTab: string
  triggerOrderTab: string
  plannedStartOrderTab: string
  emptyDeliveryOrders: string
  emptyTriggerOrders: string
  emptyPlannedStartOrders: string
  contractNo: string
  orderNo: string
  productModel: string
  materialNo: string
  quantity: string
  scheduleStatus: string
  plannedStartDate: string
  confirmedDeliveryDate: string
  triggerDate: string
  actions: string
  detailAction: string
}

export interface WorkCalendarMonthSummary {
  deliveryOrderCount: number
  deliveryQuantitySum: number
  triggerOrderCount: number
  triggerQuantitySum: number
  plannedStartOrderCount: number
  plannedStartQuantitySum: number
}

export interface WorkCalendarCell {
  key: string
  empty: boolean
  date: string
  day: number
  isToday: boolean
  summary: ScheduleCalendarDaySummary
}

export type WorkCalendarFeedbackState = 'loading' | 'ready' | 'empty' | 'error' | 'auth' | 'forbidden'

export const workCalendarLabels: WorkCalendarLabels = {
  title: '排产日历',
  subtitle: '按月查看每天的排产分布。当前展示：交付、触发、开工；点击任意日期可查看对应订单详情。',
  delivery: '交付',
  trigger: '当天触发',
  plannedStart: '开工',
  today: '今天',
  backToCurrentMonth: '返回本月',
  monthDelivery: '交付',
  monthTrigger: '本月触发',
  monthPlannedStart: '开工',
  orderUnit: '订单',
  quantityUnit: '台数',
  deliveryShort: '交付',
  triggerShort: '触发',
  plannedStartShort: '应开工',
  orderShort: '单',
  quantityShort: '台',
  detailTitleSuffix: '排产详情',
  deliveryOrderTab: '交付订单',
  triggerOrderTab: '触发订单',
  plannedStartOrderTab: '应开工订单',
  emptyDeliveryOrders: '当天没有交付订单',
  emptyTriggerOrders: '当天没有触发订单',
  emptyPlannedStartOrders: '当天没有应开工订单',
  contractNo: BUSINESS_TERMS.contractNo,
  orderNo: BUSINESS_TERMS.salesOrderNo,
  productModel: '产品型号',
  materialNo: '物料号',
  quantity: '数量',
  scheduleStatus: '排产状态',
  plannedStartDate: BUSINESS_TERMS.plannedStartDate,
  confirmedDeliveryDate: BUSINESS_TERMS.confirmedDeliveryDate,
  triggerDate: '触发日期',
  actions: '操作',
  detailAction: '详情',
}

export const workCalendarWeekdayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const createEmptySummary = (dateStr: string): ScheduleCalendarDaySummary => ({
  calendar_date: dateStr,
  delivery_order_count: 0,
  delivery_quantity_sum: 0,
  trigger_order_count: 0,
  trigger_quantity_sum: 0,
  planned_start_order_count: 0,
  planned_start_quantity_sum: 0,
})

const createEmptyDetailData = (dateStr = ''): ScheduleCalendarDayDetailResponse => ({
  summary: createEmptySummary(dateStr),
  delivery_orders: [],
  trigger_orders: [],
  planned_start_orders: [],
})

const formatDateKey = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const toNumber = (value?: string | number | null) => {
  if (value === null || value === undefined || value === '') return 0
  const num = Number(value)
  return Number.isFinite(num) ? num : 0
}

const WORK_CALENDAR_MONTH_CACHE_PREFIX = 'workCalendar:month:'
const WORK_CALENDAR_DAY_CACHE_PREFIX = 'workCalendar:day:'
const WORK_CALENDAR_MONTH_CACHE_TTL_MS = 2 * 60 * 1000
const WORK_CALENDAR_DAY_CACHE_TTL_MS = 2 * 60 * 1000

export const useWorkCalendarPage = () => {
  const router = useRouter()
  const route = useRoute()
  const monthDate = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
  const loading = ref(false)
  const calendarState = ref<WorkCalendarFeedbackState>('loading')
  const calendarStateMessage = ref('')
  const detailLoading = ref(false)
  const detailState = ref<WorkCalendarFeedbackState>('ready')
  const detailStateMessage = ref('')
  const distributionData = ref<ScheduleCalendarDaySummary[]>([])
  const detailDialogVisible = ref(false)
  const selectedDate = ref('')
  const todayStr = formatDateKey(new Date())

  const {
    sortField: deliverySortField,
    sortOrder: deliverySortOrder,
    handleSortChange: handleDeliverySortBaseChange,
    resetSort: resetDeliverySort,
  } = useTableSort()
  const {
    sortField: triggerSortField,
    sortOrder: triggerSortOrder,
    handleSortChange: handleTriggerSortBaseChange,
    resetSort: resetTriggerSort,
  } = useTableSort()
  const {
    sortField: plannedStartSortField,
    sortOrder: plannedStartSortOrder,
    handleSortChange: handlePlannedStartSortBaseChange,
    resetSort: resetPlannedStartSort,
  } = useTableSort()

  const detailData = ref<ScheduleCalendarDayDetailResponse>(createEmptyDetailData())

  const currentMonthStr = computed(() => {
    const year = monthDate.value.getFullYear()
    const month = String(monthDate.value.getMonth() + 1).padStart(2, '0')
    return `${year}-${month}`
  })
  const showCalendarState = computed(() => calendarState.value !== 'ready')
  const showDetailState = computed(() => detailState.value !== 'ready')
  const calendarFeedbackState = computed<TableFeedbackState>(() =>
    calendarState.value === 'ready' ? 'empty' : calendarState.value,
  )
  const detailFeedbackState = computed<TableFeedbackState>(() =>
    detailState.value === 'ready' ? 'empty' : detailState.value,
  )

  const distributionMap = computed(() => new Map(distributionData.value.map((item) => [item.calendar_date, item])))
  const getDaySummary = (dateStr: string) => distributionMap.value.get(dateStr) || createEmptySummary(dateStr)

  const formatQuantity = (value?: string | number | null) => {
    const num = toNumber(value)
    if (Number.isInteger(num)) return String(num)
    return num.toFixed(2).replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1')
  }

  const fetchDistributionData = async () => {
    loading.value = true
    calendarState.value = 'loading'
    calendarStateMessage.value = ''
    try {
      const month = currentMonthStr.value
      const response = await getCachedAsync(
        `${WORK_CALENDAR_MONTH_CACHE_PREFIX}${month}`,
        WORK_CALENDAR_MONTH_CACHE_TTL_MS,
        () =>
          measureAsync(
            'workCalendar',
            'fetchDistributionData',
            () =>
              request.get<ScheduleCalendarDaySummary[]>('/api/admin/work-calendar/distribution', {
                params: { month },
              }),
            { month },
          ),
      )
      distributionData.value = Array.isArray(response) ? response : []
      calendarState.value = distributionData.value.length > 0 ? 'ready' : 'empty'
    } catch (error) {
      distributionData.value = []
      calendarState.value = resolveFeedbackStateFromError(error)
      calendarStateMessage.value = resolveWorkCalendarStateMessage('calendar', calendarState.value, error)
    } finally {
      loading.value = false
    }
  }

  const calendarCells = computed<WorkCalendarCell[]>(() => {
    const year = monthDate.value.getFullYear()
    const month = monthDate.value.getMonth()
    const firstDay = new Date(year, month, 1)
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const startOffset = (firstDay.getDay() + 6) % 7

    const cells: WorkCalendarCell[] = []

    for (let i = 0; i < startOffset; i += 1) {
      cells.push({
        key: `empty-start-${i}`,
        empty: true,
        date: '',
        day: 0,
        isToday: false,
        summary: createEmptySummary(''),
      })
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const date = new Date(year, month, day)
      const dateStr = formatDateKey(date)
      cells.push({
        key: dateStr,
        empty: false,
        date: dateStr,
        day,
        isToday: dateStr === todayStr,
        summary: getDaySummary(dateStr),
      })
    }

    while (cells.length % 7 !== 0) {
      cells.push({
        key: `empty-end-${cells.length}`,
        empty: true,
        date: '',
        day: 0,
        isToday: false,
        summary: createEmptySummary(''),
      })
    }

    return cells
  })

  const monthSummary = computed<WorkCalendarMonthSummary>(() =>
    distributionData.value.reduce(
      (acc, item) => {
        acc.deliveryOrderCount += item.delivery_order_count || 0
        acc.deliveryQuantitySum += toNumber(item.delivery_quantity_sum)
        acc.triggerOrderCount += item.trigger_order_count || 0
        acc.triggerQuantitySum += toNumber(item.trigger_quantity_sum)
        acc.plannedStartOrderCount += item.planned_start_order_count || 0
        acc.plannedStartQuantitySum += toNumber(item.planned_start_quantity_sum)
        return acc
      },
      {
        deliveryOrderCount: 0,
        deliveryQuantitySum: 0,
        triggerOrderCount: 0,
        triggerQuantitySum: 0,
        plannedStartOrderCount: 0,
        plannedStartQuantitySum: 0,
      },
    ),
  )

  const detailSummary = computed(() => detailData.value.summary || createEmptySummary(selectedDate.value))
  const sortedDeliveryOrders = computed(() =>
    applyLocalSort(detailData.value.delivery_orders, {
      sortField: deliverySortField.value,
      sortOrder: deliverySortOrder.value,
    }),
  )
  const sortedTriggerOrders = computed(() =>
    applyLocalSort(detailData.value.trigger_orders, {
      sortField: triggerSortField.value,
      sortOrder: triggerSortOrder.value,
    }),
  )
  const sortedPlannedStartOrders = computed(() =>
    applyLocalSort(detailData.value.planned_start_orders, {
      sortField: plannedStartSortField.value,
      sortOrder: plannedStartSortOrder.value,
    }),
  )

  const {
    pageNo: deliveryPageNo,
    pageSize: deliveryPageSize,
    pageSizes: deliveryPageSizes,
    total: deliveryTotal,
    pagedData: pagedDeliveryOrders,
    resetPagination: resetDeliveryPagination,
  } = useLocalTablePagination(() => sortedDeliveryOrders.value)
  const {
    pageNo: triggerPageNo,
    pageSize: triggerPageSize,
    pageSizes: triggerPageSizes,
    total: triggerTotal,
    pagedData: pagedTriggerOrders,
    resetPagination: resetTriggerPagination,
  } = useLocalTablePagination(() => sortedTriggerOrders.value)
  const {
    pageNo: plannedStartPageNo,
    pageSize: plannedStartPageSize,
    pageSizes: plannedStartPageSizes,
    total: plannedStartTotal,
    pagedData: pagedPlannedStartOrders,
    resetPagination: resetPlannedStartPagination,
  } = useLocalTablePagination(() => sortedPlannedStartOrders.value)

  const resetDetailSorts = () => {
    resetDeliverySort()
    resetTriggerSort()
    resetPlannedStartSort()
  }

  const resetDetailPagination = () => {
    resetDeliveryPagination()
    resetTriggerPagination()
    resetPlannedStartPagination()
  }

  const handleDeliverySortChange = (sort: { prop?: string; order?: 'ascending' | 'descending' | null }) => {
    handleDeliverySortBaseChange(sort)
  }

  const handleTriggerSortChange = (sort: { prop?: string; order?: 'ascending' | 'descending' | null }) => {
    handleTriggerSortBaseChange(sort)
  }

  const handlePlannedStartSortChange = (sort: { prop?: string; order?: 'ascending' | 'descending' | null }) => {
    handlePlannedStartSortBaseChange(sort)
  }

  const changeMonth = (delta: number) => {
    monthDate.value = new Date(monthDate.value.getFullYear(), monthDate.value.getMonth() + delta, 1)
  }

  const goToCurrentMonth = () => {
    const now = new Date()
    monthDate.value = new Date(now.getFullYear(), now.getMonth(), 1)
  }

  const openDayDetail = async (dateStr: string) => {
    if (!dateStr) return
    resetDetailSorts()
    resetDetailPagination()
    selectedDate.value = dateStr
    detailDialogVisible.value = true
    detailLoading.value = true
    detailState.value = 'loading'
    detailStateMessage.value = ''
    try {
      const response = await getCachedAsync(
        `${WORK_CALENDAR_DAY_CACHE_PREFIX}${dateStr}`,
        WORK_CALENDAR_DAY_CACHE_TTL_MS,
        () =>
          measureAsync(
            'workCalendar',
            'openDayDetail',
            () =>
              request.get<ScheduleCalendarDayDetailResponse>('/api/admin/work-calendar/day-detail', {
                params: { date: dateStr },
              }),
            { date: dateStr },
          ),
      )
      detailData.value = {
        summary: response?.summary || createEmptySummary(dateStr),
        delivery_orders: Array.isArray(response?.delivery_orders) ? response.delivery_orders : [],
        trigger_orders: Array.isArray(response?.trigger_orders) ? response.trigger_orders : [],
        planned_start_orders: Array.isArray(response?.planned_start_orders) ? response.planned_start_orders : [],
      }
      detailState.value = 'ready'
    } catch (error) {
      detailData.value = createEmptyDetailData(dateStr)
      detailState.value = resolveFeedbackStateFromError(error)
      detailStateMessage.value = resolveWorkCalendarStateMessage('detail', detailState.value, error)
    } finally {
      detailLoading.value = false
    }
  }

  const goToScheduleDetail = (orderLineId: number) => {
    detailDialogVisible.value = false
    router.push(`/schedules/${orderLineId}`)
  }

  const handleCalendarStateAction = async () => {
    if (calendarState.value === 'auth') {
      await router.push({
        name: 'AdminAuth',
        query: { redirect: route.fullPath },
      })
      return
    }
    if (calendarState.value === 'error') {
      await fetchDistributionData()
    }
  }

  const handleDetailStateAction = async () => {
    if (detailState.value === 'auth') {
      await router.push({
        name: 'AdminAuth',
        query: { redirect: route.fullPath },
      })
      return
    }
    if (detailState.value === 'error' && selectedDate.value) {
      await openDayDetail(selectedDate.value)
    }
  }

  watch(detailDialogVisible, (visible) => {
    if (!visible) {
      resetDetailSorts()
      resetDetailPagination()
    }
  })

  watch(currentMonthStr, () => {
    void fetchDistributionData()
  })

  onMounted(() => {
    void fetchDistributionData()
  })

  return {
    calendarCells,
    calendarState,
    calendarFeedbackState,
    calendarStateMessage,
    changeMonth,
    currentMonthStr,
    deliveryPageNo,
    deliveryPageSize,
    deliveryPageSizes,
    deliveryTotal,
    detailData,
    detailDialogVisible,
    detailLoading,
    detailFeedbackState,
    detailState,
    detailStateMessage,
    detailSummary,
    formatQuantity,
    goToCurrentMonth,
    goToScheduleDetail,
    handleCalendarStateAction,
    handleDeliverySortChange,
    handlePlannedStartSortChange,
    handleDetailStateAction,
    handleTriggerSortChange,
    labels: workCalendarLabels,
    loading,
    monthSummary,
    openDayDetail,
    pagedDeliveryOrders,
    pagedPlannedStartOrders,
    pagedTriggerOrders,
    plannedStartPageNo,
    plannedStartPageSize,
    plannedStartPageSizes,
    plannedStartTotal,
    selectedDate,
    showCalendarState,
    showDetailState,
    triggerPageNo,
    triggerPageSize,
    triggerPageSizes,
    triggerTotal,
    weekdayLabels: workCalendarWeekdayLabels,
  }
}

function resolveFeedbackStateFromError(error: unknown): WorkCalendarFeedbackState {
  const status = typeof error === 'object' && error && 'status' in error ? (error as { status?: number }).status : undefined
  if (status === 401) return 'auth'
  if (status === 403) return 'forbidden'
  return 'error'
}

function resolveWorkCalendarStateMessage(
  scope: 'calendar' | 'detail',
  state: WorkCalendarFeedbackState,
  error: unknown,
) {
  const message = error instanceof Error ? error.message.trim() : ''
  if (state === 'auth') {
    return scope === 'calendar'
      ? '登录状态已失效，请重新登录后再查看排产日历。'
      : '登录状态已失效，请重新登录后再查看当日排产明细。'
  }
  if (state === 'forbidden') {
    return scope === 'calendar'
      ? '当前账号无权查看排产日历，请使用具备权限的账号访问。'
      : '当前账号无权查看当日排产明细，请使用具备权限的账号访问。'
  }
  if (message) return message
  return scope === 'calendar'
    ? '排产日历加载失败，请稍后重试。'
    : '当日排产明细加载失败，请稍后重试。'
}
