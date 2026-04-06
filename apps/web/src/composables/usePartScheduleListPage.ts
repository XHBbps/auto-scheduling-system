import axios from 'axios'
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useServerTableQuery } from './useServerTableQuery'
import { useExportAction } from './useExportAction'
import { useRequestCancellation } from './useRequestCancellation'
import { useTableFeedbackState } from './useTableFeedbackState'
import { getTableSortColumnProps } from './useTableSort'
import request from '../utils/httpClient'
import { measureAsync } from '../utils/performance'
import { getCachedAsync } from '../utils/requestCache'
import type { PaginatedResponse, PartScheduleItem } from '../types/apiModels'

export interface PartScheduleSearchForm {
  orderNo: string
  contractNo: string
  assemblyName: string
  partMaterialNo: string
  warningLevel: string
}

export type PartScheduleOptionalColumnKey =
  | 'customer_name'
  | 'product_series'
  | 'product_model'
  | 'product_name'
  | 'material_no'
  | 'order_type'
  | 'custom_no'
  | 'business_group'
  | 'sales_person_name'
  | 'sales_branch_company'
  | 'sales_sub_branch'
  | 'order_date'
  | 'confirmed_delivery_date'
  | 'line_total_amount'

export interface PartScheduleColumnOption {
  key: PartScheduleOptionalColumnKey
  label: string
}

const COLUMN_VISIBILITY_STORAGE_KEY = 'part-schedule-list-visible-columns'
const ASSEMBLY_OPTIONS_CACHE_KEY = 'partScheduleList:assemblyOptions'
const ASSEMBLY_OPTIONS_CACHE_TTL_MS = 10 * 60 * 1000

const createSearchForm = (): PartScheduleSearchForm => ({
  orderNo: '',
  contractNo: '',
  assemblyName: '',
  partMaterialNo: '',
  warningLevel: '',
})

const optionalColumns: PartScheduleColumnOption[] = [
  { key: 'customer_name', label: '客户名称' },
  { key: 'product_series', label: '产品系列' },
  { key: 'product_model', label: '产品型号' },
  { key: 'product_name', label: '产品名称' },
  { key: 'material_no', label: '整机物料号' },
  { key: 'order_type', label: '订单类型' },
  { key: 'custom_no', label: '定制号' },
  { key: 'business_group', label: '事业群' },
  { key: 'sales_person_name', label: '销售人员' },
  { key: 'sales_branch_company', label: '分公司' },
  { key: 'sales_sub_branch', label: '支公司' },
  { key: 'order_date', label: '订单日期' },
  { key: 'confirmed_delivery_date', label: '确认交货期' },
  { key: 'line_total_amount', label: '合同金额' },
]

const optionalColumnKeySet = new Set<PartScheduleOptionalColumnKey>(
  optionalColumns.map((column) => column.key),
)
const defaultVisibleColumnKeys = optionalColumns.map((column) => column.key)

const normalizeVisibleColumnKeys = (value: unknown): PartScheduleOptionalColumnKey[] => {
  if (!Array.isArray(value)) return [...defaultVisibleColumnKeys]
  return value.filter((item): item is PartScheduleOptionalColumnKey =>
    optionalColumnKeySet.has(item as PartScheduleOptionalColumnKey),
  )
}

export const usePartScheduleListPage = () => {
  const sortableColumnProps = getTableSortColumnProps()
  const { exporting, runConfirmedExport } = useExportAction()
  const { newSignal } = useRequestCancellation()
  const { tableFeedbackState, showLoadingState, showEmptyState, showErrorState } = useTableFeedbackState()
  const router = useRouter()
  const route = useRoute()

  const dateRange = ref<[string, string] | null>(null)
  const loading = ref(false)
  const tableData = ref<PartScheduleItem[]>([])
  const assemblyOptions = ref<string[]>([])
  const visibleColumnKeys = ref<PartScheduleOptionalColumnKey[]>([...defaultVisibleColumnKeys])

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
      orderNo: 'order_no',
      contractNo: 'contract_no',
      assemblyName: 'assembly_name',
      partMaterialNo: 'part_material_no',
      warningLevel: 'warning_level',
    },
    buildExtraParams: () => {
      if (!dateRange.value || dateRange.value.length !== 2) {
        return {}
      }
      return {
        date_from: dateRange.value[0],
        date_to: dateRange.value[1],
      }
    },
    resetExtraState: () => {
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

  const fetchAssemblyOptions = async () => {
    try {
      const res = await getCachedAsync(ASSEMBLY_OPTIONS_CACHE_KEY, ASSEMBLY_OPTIONS_CACHE_TTL_MS, () =>
        measureAsync('partScheduleList', 'fetchAssemblyOptions', () =>
          request.get<string[]>('/api/part-schedules/options/assembly-names'),
        ),
      )
      assemblyOptions.value = res || []
    } catch (error) {
      console.error(error)
    }
  }

  const fetchData = async () => {
    loading.value = true
    showLoadingState()
    const signal = newSignal()
    try {
      const params = buildQueryParams()
      const res = await measureAsync(
        'partScheduleList',
        'fetchData',
        () =>
          request.get<PaginatedResponse<PartScheduleItem>>('/api/part-schedules', {
            params,
            signal,
            silentError: true,
          }),
        {
          pageNo: pageNo.value,
          pageSize: pageSize.value,
          hasDateRange: Boolean(dateRange.value?.length === 2),
        },
      )
      tableData.value = res.items || []
      showEmptyState()
      setTotal(res.total)
    } catch (error) {
      if (axios.isCancel(error)) return
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

  const handleExport = async () => {
    await runConfirmedExport({
      confirmTitle: '导出零件排产列表',
      confirmMessage: '确认导出当前筛选条件下的零件排产列表吗？系统将立即生成并开始下载文件。',
      fallbackFilename: `零件排产列表_${Date.now()}.xlsx`,
      successMessage: '零件排产列表导出成功，已开始下载',
      failureMessage: '零件排产列表导出失败，请稍后重试',
      request: () =>
        request.get('/api/exports/part-schedules', {
          params: buildQueryParams({ includePagination: false }),
          responseType: 'blob',
          silentError: true,
        }),
    })
  }

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

  const goToScheduleList = (row: PartScheduleItem) => {
    router.push({ path: '/schedules', query: { contract_no: row.contract_no } })
  }

  const formatAssemblyDays = (value?: number | string | null) => {
    if (value === null || value === undefined || value === '') return '-'
    const num = Number(value)
    if (Number.isNaN(num)) return String(value)
    return String(Math.trunc(num))
  }

  const formatCycleDays = (value?: number | string | null) => {
    if (value === null || value === undefined || value === '') return '-'
    const num = Number(value)
    if (Number.isNaN(num)) return String(value)
    if (Number.isInteger(num)) return String(num)
    return num.toFixed(2).replace(/\.?0+$/, '')
  }

  const formatQuantity = (value?: number | string | null) => {
    if (value === null || value === undefined || value === '') return '-'
    const num = Number(value)
    if (Number.isNaN(num)) return String(value)
    if (Number.isInteger(num)) return String(num)
    return num.toFixed(2).replace(/\.?0+$/, '')
  }

  const formatAmount = (value?: number | string | null) => {
    if (value === null || value === undefined || value === '') return '-'
    const num = Number(value)
    if (Number.isNaN(num)) return String(value)
    return new Intl.NumberFormat('zh-CN', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(num)
  }

  onMounted(() => {
    if (route.query.contract_no) searchForm.value.contractNo = route.query.contract_no as string
    if (route.query.order_no) searchForm.value.orderNo = route.query.order_no as string
    if (route.query.assembly_name) searchForm.value.assemblyName = route.query.assembly_name as string
    if (route.query.part_material_no) searchForm.value.partMaterialNo = route.query.part_material_no as string
    if (route.query.warning_level) searchForm.value.warningLevel = route.query.warning_level as string

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
    fetchAssemblyOptions()
    fetchData()
  })

  return {
    assemblyOptions,
    exporting,
    dateRange,
    fetchData,
    formatAmount,
    formatAssemblyDays,
    formatCycleDays,
    formatQuantity,
    goToScheduleList,
    handleExport,
    handleReset,
    handleSearch,
    handleTableSortChange,
    handleTableStateAction,
    loading,
    optionalColumns,
    pageNo,
    pageSize,
    pageSizes,
    resetVisibleColumns,
    searchForm,
    sortableColumnProps,
    tableData,
    tableFeedbackState,
    total,
    visibleColumnKeys,
  }
}


