import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useServerTableQuery } from './useServerTableQuery'
import { useTableFeedbackState } from './useTableFeedbackState'
import { useRequestCancellation } from './useRequestCancellation'
import { applyLocalSort, getTableSortColumnProps } from './useTableSort'
import { usePartCycleBaselineDialog } from './usePartCycleBaselineDialog'
import request from '../utils/httpClient'
import { getActiveStatusBadgeMeta } from '../utils/statusPresentation'
import { showStructuredConfirmDialog } from '../utils/confirmDialog'

export interface PartCycleItem {
  id: number
  part_type?: string
  material_no: string
  material_desc: string
  core_part_name?: string
  machine_model?: string
  plant?: string | null
  ref_batch_qty: number
  cycle_days: number
  unit_cycle_days: number
  sample_count?: number
  source_updated_at?: string | null
  cycle_source?: string
  match_rule?: string
  confidence_level?: string
  is_default?: boolean
  is_active: boolean
  remark?: string
}

interface TriggerResponse {
  job_id?: number | null
  status: string
  message: string
}

export interface PartCycleSearchForm {
  part_type: string
  machine_model: string
  plant: string
}

const createSearchForm = (): PartCycleSearchForm => ({
  part_type: '',
  machine_model: '',
  plant: '',
})

export const usePartCycleBaselinePage = () => {
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
    sortField,
    sortOrder,
    buildQueryParams,
    handleSearch: triggerSearch,
    handleReset: triggerReset,
    handleTableSortChange: triggerTableSortChange,
    setTotal,
  } = useServerTableQuery({
    createSearchForm,
  })

  const loading = ref(false)
  const rebuildLoading = ref(false)
  const tableData = ref<PartCycleItem[]>([])
  const sortedTableData = computed(() =>
    applyLocalSort(tableData.value, {
      sortField: sortField.value,
      sortOrder: sortOrder.value,
    }),
  )
  const pagedTableData = computed(() => {
    const start = (pageNo.value - 1) * pageSize.value
    return sortedTableData.value.slice(start, start + pageSize.value)
  })

  const cycleSourceLabelMap: Record<string, string> = {
    manual: '手工维护',
    history: '历史回算',
  }

  const resolvePartType = (row: PartCycleItem) => row.part_type || row.core_part_name || row.material_no || '-'

  const handleDelete = async (row: PartCycleItem) => {
    try {
      await showStructuredConfirmDialog({
        title: '删除确认',
        badge: '删除基准',
        headline: `确认删除【${resolvePartType(row)} / ${row.machine_model || '-'} / ${row.plant || '通用'}】这条记录吗？`,
        description: '删除后该零件周期基准会从列表移除，后续需要手工维护或重新触发重建。',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }

    try {
      await request.delete(`/api/admin/part-cycle-baselines/${row.id}`)
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
        badge: '重建零件基准',
        headline: '确认立即重建零件周期基准吗？',
        description: '系统会按当前样本重新计算零件周期基准，并在后台任务执行后刷新页面结果。',
        confirmButtonText: '确认重建',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }

    rebuildLoading.value = true
    try {
      const res = await request.post<TriggerResponse>('/api/admin/part-cycle-baselines/rebuild', {})
      ElMessage.success(res.message || '零件周期基准重建任务已触发')
    } catch (error) {
      console.error(error)
    } finally {
      rebuildLoading.value = false
    }
  }

  const fetchData = async () => {
    loading.value = true
    showLoadingState()
    const signal = newSignal()
    try {
      const res = await request.get<PartCycleItem[]>('/api/admin/part-cycle-baselines', {
        params: buildQueryParams({ includePagination: false }),
        silentError: true,
        signal,
      })
      tableData.value = Array.isArray(res) ? res : []
      setTotal(tableData.value.length)
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
  const handleTableSortChange = (sort: { prop?: string; order?: 'ascending' | 'descending' | null }) => {
    triggerTableSortChange(sort, () => undefined)
  }

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
    usePartCycleBaselineDialog({
      resolvePartType,
      onSubmitted: fetchData,
    })

  onMounted(() => {
    void fetchData()
  })

  return {
    sortableColumnProps,
    loading,
    rebuildLoading,
    tableData,
    pagedTableData,
    tableFeedbackState,
    searchForm,
    pageNo,
    pageSize,
    pageSizes,
    total,
    cycleSourceLabelMap,
    dialogVisible,
    isEdit,
    submitting,
    form,
    rules,
    fetchData,
    resolvePartType,
    handleAdd,
    handleEdit,
    handleDelete,
    handleSubmit,
    handleRebuild,
    handleSearch,
    handleReset,
    handleTableSortChange,
    handleTableStateAction,
    getActiveStatusBadgeMeta,
  }
}

