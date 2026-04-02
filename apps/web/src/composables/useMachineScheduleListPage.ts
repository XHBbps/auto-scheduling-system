import { h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useServerTableQuery } from './useServerTableQuery'
import { useExportAction } from './useExportAction'
import { useTableFeedbackState } from './useTableFeedbackState'
import { getTableSortColumnProps } from './useTableSort'
import { ensureAuthSession, getAuthSessionState } from '../utils/authSession'
import { formatDate } from '../utils/format'
import request from '../utils/httpClient'
import { hasPermissionCode } from '../utils/accessControl'
import { measureAsync } from '../utils/performance'
import { getCachedAsync } from '../utils/requestCache'
import type {
  MachineScheduleItem,
  PaginatedResponse,
  PartScheduleRunOneResponse,
  ScheduleValidationItem,
} from '../types/apiModels'

export interface MachineScheduleSearchForm {
  contractNo: string
  customerName: string
  productSeries: string
  productModel: string
  orderNo: string
  scheduleStatus: string
  warningLevel: string
}

export type MachineScheduleOptionalColumnKey =
  | 'product_name'
  | 'custom_no'
  | 'business_group'
  | 'sales_person_name'
  | 'sales_branch_company'
  | 'sales_sub_branch'
  | 'sap_code'
  | 'sap_line_no'
  | 'order_date'
  | 'line_total_amount'
  | 'custom_requirement'
  | 'review_comment'
  | 'warning_level'

export interface MachineScheduleColumnOption {
  key: MachineScheduleOptionalColumnKey
  label: string
}

export interface MachineScheduleRunActionState {
  disabled: boolean
  reason: string
}

const COLUMN_VISIBILITY_STORAGE_KEY = 'schedule-list-visible-columns'
const PRODUCT_SERIES_OPTIONS_CACHE_KEY = 'machineScheduleList:productSeriesOptions'
const PRODUCT_SERIES_OPTIONS_CACHE_TTL_MS = 10 * 60 * 1000

const createSearchForm = (): MachineScheduleSearchForm => ({
  contractNo: '',
  customerName: '',
  productSeries: '',
  productModel: '',
  orderNo: '',
  scheduleStatus: '',
  warningLevel: '',
})

const optionalColumns: MachineScheduleColumnOption[] = [
  { key: 'product_name', label: '产品名称' },
  { key: 'custom_no', label: '定制号' },
  { key: 'business_group', label: '事业群' },
  { key: 'sales_person_name', label: '销售人员' },
  { key: 'sales_branch_company', label: '分公司' },
  { key: 'sales_sub_branch', label: '支公司' },
  { key: 'sap_code', label: 'SAP编码' },
  { key: 'sap_line_no', label: 'SAP行号' },
  { key: 'order_date', label: '订单日期' },
  { key: 'line_total_amount', label: '合同金额' },
  { key: 'custom_requirement', label: '定制要求' },
  { key: 'review_comment', label: '评审意见' },
  { key: 'warning_level', label: '异常标识' },
]

const optionalColumnKeySet = new Set<MachineScheduleOptionalColumnKey>(
  optionalColumns.map((column) => column.key),
)
const defaultVisibleColumnKeys = optionalColumns.map((column) => column.key)

const normalizeVisibleColumnKeys = (value: unknown): MachineScheduleOptionalColumnKey[] => {
  if (!Array.isArray(value)) return [...defaultVisibleColumnKeys]
  return value.filter((item): item is MachineScheduleOptionalColumnKey =>
    optionalColumnKeySet.has(item as MachineScheduleOptionalColumnKey),
  )
}

const formatValidationAlert = (items: ScheduleValidationItem[]) =>
  items.map((item) => `• ${item.label}：${item.message}`).join('\n')

export const useMachineScheduleListPage = () => {
  const sortableColumnProps = getTableSortColumnProps()
  const router = useRouter()
  const route = useRoute()
  const { exporting, runConfirmedExport } = useExportAction()
  const { tableFeedbackState, showLoadingState, showEmptyState, showErrorState } = useTableFeedbackState()

  const dateRange = ref<[string, string] | null>(null)
  const scheduleBucket = ref('')
  const loading = ref(false)
  const tableData = ref<MachineScheduleItem[]>([])
  const partScheduleLoading = ref<Record<number, boolean>>({})
  const productSeriesOptions = ref<string[]>([])
  const visibleColumnKeys = ref<MachineScheduleOptionalColumnKey[]>([...defaultVisibleColumnKeys])

  const {
    searchForm,
    pageNo,
    pageSize,
    pageSizes,
    total,
    buildQueryParams,
    handleSearch: triggerSearch,
    handleReset: triggerReset,
    handleTableSortChange: triggerTableSortChange,
    setTotal,
  } = useServerTableQuery({
    createSearchForm,
    searchParamKeyMap: {
      contractNo: 'contract_no',
      customerName: 'customer_name',
      productSeries: 'product_series',
      productModel: 'product_model',
      orderNo: 'order_no',
      scheduleStatus: 'schedule_status',
      warningLevel: 'warning_level',
    },
    buildExtraParams: () => ({
      schedule_bucket: scheduleBucket.value,
      ...(dateRange.value?.length === 2
        ? {
            date_from: dateRange.value[0],
            date_to: dateRange.value[1],
          }
        : {}),
    }),
    resetExtraState: () => {
      scheduleBucket.value = ''
      dateRange.value = null
    },
  })

  const resetVisibleColumns = () => {
    visibleColumnKeys.value = [...defaultVisibleColumnKeys]
  }

  const loadVisibleColumns = () => {
    if (typeof window === 'undefined') return
    try {
      const raw = window.localStorage.getItem(COLUMN_VISIBILITY_STORAGE_KEY)
      if (!raw) return
      visibleColumnKeys.value = normalizeVisibleColumnKeys(JSON.parse(raw))
    } catch (error) {
      console.error(error)
      visibleColumnKeys.value = [...defaultVisibleColumnKeys]
    }
  }

  watch(
    visibleColumnKeys,
    (value) => {
      if (typeof window === 'undefined') return
      window.localStorage.setItem(COLUMN_VISIBILITY_STORAGE_KEY, JSON.stringify(value))
    },
    { deep: true },
  )

  const formatMachineQuantity = (value?: number | string | null) => {
    if (value === null || value === undefined || value === '') return '-'
    const num = Number(value)
    if (Number.isFinite(num)) {
      return Number.isInteger(num) ? String(num) : String(num).replace(/\.?0+$/, '')
    }
    return String(value)
  }

  const formatAmount = (value?: number | string | null) => {
    if (value === null || value === undefined) return '-'
    const numeric = Number(value)
    if (Number.isNaN(numeric)) return String(value)
    return new Intl.NumberFormat('zh-CN', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(numeric)
  }

  const fetchProductSeriesOptions = async () => {
    try {
      const res = await getCachedAsync(PRODUCT_SERIES_OPTIONS_CACHE_KEY, PRODUCT_SERIES_OPTIONS_CACHE_TTL_MS, () =>
        measureAsync('machineScheduleList', 'fetchProductSeriesOptions', () =>
          request.get('/api/schedules/options/product-series'),
        ),
      )
      productSeriesOptions.value = res || []
    } catch (error) {
      console.error(error)
    }
  }

  const fetchData = async () => {
    loading.value = true
    showLoadingState()
    try {
      const params = buildQueryParams()
      const res = await measureAsync(
        'machineScheduleList',
        'fetchData',
        () =>
          request.get<PaginatedResponse<MachineScheduleItem>>('/api/schedules', {
            params,
            silentError: true,
          }),
        {
          pageNo: pageNo.value,
          pageSize: pageSize.value,
          hasDateRange: Boolean(dateRange.value?.length === 2),
          scheduleBucket: scheduleBucket.value || '',
        },
      )
      tableData.value = res.items || []
      showEmptyState()
      setTotal(res.total)
    } catch (error) {
      console.error(error)
      showErrorState(error)
    } finally {
      loading.value = false
    }
  }

  const handleSearch = () => triggerSearch(fetchData)

  const handleReset = () => triggerReset(fetchData)

  const handleTableSortChange = (sort: { prop?: string; order?: 'ascending' | 'descending' | null }) =>
    triggerTableSortChange(sort, fetchData)

  const handleTableStateAction = async () => {
    if (tableFeedbackState.value === 'auth') {
      router.push({
        name: 'AdminAuth',
        query: {
          redirect: route.fullPath,
        },
      })
      return
    }

    if (tableFeedbackState.value === 'error') {
      await fetchData()
    }
  }

  const handleExport = async () => {
    await runConfirmedExport({
      confirmTitle: '导出整机排产列表',
      confirmMessage: '确认导出当前筛选条件下的整机排产列表吗？系统将立即生成并开始下载文件。',
      fallbackFilename: `整机排产列表_${Date.now()}.xlsx`,
      successMessage: '整机排产列表导出成功，已开始下载',
      failureMessage: '整机排产列表导出失败，请稍后重试',
      request: () =>
        request.get('/api/exports/machine-schedules', {
          params: buildQueryParams(),
          responseType: 'blob',
          silentError: true,
        }),
    })
  }

  const getRunActionState = (row: MachineScheduleItem): MachineScheduleRunActionState => {
    if (!hasPermissionCode(getAuthSessionState(), 'schedule.manage')) {
      return {
        disabled: true,
        reason: '当前账号没有执行排产的权限。',
      }
    }

    const status = row.schedule_status || ''
    if (status === 'schedulable' || status === 'scheduled' || status === 'scheduled_stale') {
      return {
        disabled: false,
        reason: '',
      }
    }

    if (status === 'pending_drawing') {
      return {
        disabled: true,
        reason: row.confirmed_delivery_date
          ? '当前订单仍处于待图纸下发状态，暂不支持生成零件排产。'
          : '当前订单尚未满足图纸下发条件，暂不支持生成零件排产。',
      }
    }

    if (status === 'pending_trigger') {
      return {
        disabled: true,
        reason: row.trigger_date
          ? `当前订单需等待触发日期 ${formatDate(row.trigger_date)} 后才能生成零件排产。`
          : '当前订单尚未到达触发条件，暂不支持生成零件排产。',
      }
    }

    if (status === 'missing_bom') {
      return {
        disabled: true,
        reason: '当前订单缺少 BOM 数据，暂不支持生成零件排产。',
      }
    }

    return {
      disabled: true,
      reason: '当前排产状态不支持生成零件排产。',
    }
  }

  const showValidationAlert = async (title: string, items: ScheduleValidationItem[]) => {
    if (!items.length) return
    await ElMessageBox.alert(
      h(
        'div',
        {
          class: 'whitespace-pre-line text-sm leading-6 text-text-secondary',
        },
        formatValidationAlert(items),
      ),
      title,
      {
        confirmButtonText: '我知道了',
      },
    )
  }

  const handleRunPartSchedule = async (row: MachineScheduleItem) => {
    if (partScheduleLoading.value[row.order_line_id]) return
    if (!(await ensureAuthSession({ forceRefresh: true, requiredPermissions: ['schedule.manage'] }))) {
      const authState = getAuthSessionState()
      if (!authState.authenticated) {
        router.push({
          name: 'AdminAuth',
          query: {
            redirect: route.fullPath,
          },
        })
        return
      }
      ElMessage.error('当前账号没有执行排产的权限')
      return
    }

    partScheduleLoading.value = {
      ...partScheduleLoading.value,
      [row.order_line_id]: true,
    }

    try {
      const res = await request.post<PartScheduleRunOneResponse>('/api/admin/schedule/run-one-part', {
        order_line_id: row.order_line_id,
      })

      const blockingItems = (res.validation_items || []).filter((item) => item.level === 'blocking')
      if (!res.success) {
        if (blockingItems.length) {
          await showValidationAlert('零件排产前置校验未通过', blockingItems)
        } else {
          ElMessage.error(res.message || '生成零件排产失败')
        }
        return
      }

      ElMessage.success(res.message || '零件排产生成成功')
      if (res.warning_summary) {
        ElMessage.warning(res.warning_summary)
      }
      await fetchData()
    } catch (error) {
      console.error(error)
    } finally {
      partScheduleLoading.value = {
        ...partScheduleLoading.value,
        [row.order_line_id]: false,
      }
    }
  }

  const goToDetail = (row: MachineScheduleItem) => {
    router.push(`/schedules/${row.order_line_id}`)
  }

  onMounted(() => {
    if (route.query.contract_no) searchForm.value.contractNo = route.query.contract_no as string
    if (route.query.customer_name) searchForm.value.customerName = route.query.customer_name as string
    if (route.query.product_series) searchForm.value.productSeries = route.query.product_series as string
    if (route.query.product_model) searchForm.value.productModel = route.query.product_model as string
    if (route.query.order_no) searchForm.value.orderNo = route.query.order_no as string
    if (route.query.schedule_status) searchForm.value.scheduleStatus = route.query.schedule_status as string
    if (route.query.warning_level) searchForm.value.warningLevel = route.query.warning_level as string
    if (route.query.schedule_bucket) scheduleBucket.value = route.query.schedule_bucket as string

    const queryDateFrom = route.query.date_from as string | undefined
    const queryDateTo = route.query.date_to as string | undefined
    if (queryDateFrom || queryDateTo) {
      const start = queryDateFrom || queryDateTo || ''
      const end = queryDateTo || queryDateFrom || ''
      if (start && end) {
        dateRange.value = [start, end]
      }
    }

    loadVisibleColumns()
    fetchProductSeriesOptions()
    fetchData()
  })

  return {
    dateRange,
    exporting,
    fetchData,
    formatAmount,
    formatMachineQuantity,
    getRunActionState,
    goToDetail,
    handleExport,
    handleReset,
    handleRunPartSchedule,
    handleSearch,
    handleTableSortChange,
    handleTableStateAction,
    loading,
    optionalColumns,
    pageNo,
    pageSize,
    pageSizes,
    partScheduleLoading,
    productSeriesOptions,
    resetVisibleColumns,
    searchForm,
    sortableColumnProps,
    tableData,
    tableFeedbackState,
    total,
    visibleColumnKeys,
  }
}


