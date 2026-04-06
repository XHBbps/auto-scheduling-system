import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useServerTableQuery } from './useServerTableQuery'
import { useTableFeedbackState } from './useTableFeedbackState'
import { useRequestCancellation } from './useRequestCancellation'
import { useMachineCycleBaselineDialog } from './useMachineCycleBaselineDialog'
import request from '../utils/httpClient'
import { getTableSortColumnProps } from './useTableSort'
import { showStructuredConfirmDialog } from '../utils/confirmDialog'
import { getActiveStatusBadgeMeta } from '../utils/statusPresentation'

export interface MachineCycleItem {
  id: number
  product_series?: string
  machine_model: string
  order_qty: number
  cycle_days_median: number
  sample_count: number
  is_active: boolean
  remark?: string
}

interface PaginatedResponse {
  total: number
  page_no: number
  page_size: number
  items: MachineCycleItem[]
}

export interface MachineCycleSearchForm {
  machine_model: string
  product_series: string
}

const createSearchForm = (): MachineCycleSearchForm => ({
  machine_model: '',
  product_series: '',
})

export const useMachineCycleBaselinePage = () => {
  const { newSignal } = useRequestCancellation()
  const sortableColumnProps = getTableSortColumnProps()
  const router = useRouter()
  const route = useRoute()
  const { tableFeedbackState, showLoadingState, showEmptyState, showErrorState } = useTableFeedbackState()

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
  })

  const loading = ref(false)
  const rebuilding = ref(false)
  const tableData = ref<MachineCycleItem[]>([])

  const handleDelete = async (row: MachineCycleItem) => {
    try {
      await showStructuredConfirmDialog({
        title: '删除确认',
        badge: '删除基准',
        headline: `确认删除【${row.machine_model} / 数量 ${row.order_qty}】这条记录吗？`,
        description: '删除后该整机周期基准会从列表移除，后续维护需重新录入或重建。',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }

    try {
      await request.delete(`/api/admin/machine-cycle-baselines/${row.id}`)
      ElMessage.success('删除成功')
      await fetchData()
    } catch (error) {
      console.error(error)
    }
  }

  const handleRebuild = async () => {
    try {
      await showStructuredConfirmDialog({
        title: '确认重建基准',
        badge: '重建整机基准',
        headline: '确认立即重建整机周期基准吗？',
        description: '系统会按当前历史样本重新计算整机周期中位数，并刷新列表展示结果。',
        confirmButtonText: '确认重建',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }

    rebuilding.value = true
    try {
      const res = await request.post<{ groups_processed: number; total_samples: number }>(
        '/api/admin/machine-cycle-baselines/rebuild',
      )
      ElMessage.success(`重建完成：${res.groups_processed}组 / ${res.total_samples}条样本`)
      await fetchData()
    } catch (error) {
      console.error(error)
    } finally {
      rebuilding.value = false
    }
  }

  const fetchData = async () => {
    loading.value = true
    showLoadingState()
    const signal = newSignal()
    try {
      const res = await request.get<PaginatedResponse | MachineCycleItem[]>('/api/admin/machine-cycle-baselines', {
        params: buildQueryParams(),
        silentError: true,
        signal,
      })
      if (Array.isArray(res)) {
        setTotal(res.length)
        const start = (pageNo.value - 1) * pageSize.value
        tableData.value = res.slice(start, start + pageSize.value)
      } else {
        tableData.value = res.items || []
        setTotal(res.total || 0)
      }
      showEmptyState()
    } catch (error) {
      if (axios.isCancel(error)) return
      console.error(error)
      tableData.value = []
      setTotal(0)
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
      await router.push({
        name: 'AdminAuth',
        query: { redirect: route.fullPath },
      })
      return
    }

    if (tableFeedbackState.value === 'error') {
      await fetchData()
    }
  }

  const { dialogVisible, isEdit, submitting, form, rules, handleAdd, handleEdit, handleSubmit } =
    useMachineCycleBaselineDialog({
      onSubmitted: fetchData,
    })

  onMounted(() => {
    void fetchData()
  })

  return {
    sortableColumnProps,
    loading,
    rebuilding,
    tableData,
    tableFeedbackState,
    searchForm,
    pageNo,
    pageSize,
    pageSizes,
    total,
    dialogVisible,
    isEdit,
    submitting,
    form,
    rules,
    fetchData,
    handleAdd,
    handleEdit,
    handleDelete,
    handleRebuild,
    handleSubmit,
    handleSearch,
    handleReset,
    handleTableSortChange,
    handleTableStateAction,
    getActiveStatusBadgeMeta,
  }
}

