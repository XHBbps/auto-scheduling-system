import { computed, onMounted, ref, watch } from 'vue'
import type { FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { useLocalTablePagination } from './useTablePagination'
import { applyLocalSort, type TableSortChange, useTableSort } from './useTableSort'
import request from '../utils/httpClient'
import { cleanParams } from '../utils/format'
import { showStructuredConfirmDialog } from '../utils/confirmDialog'
import type { AssemblyTimeItem } from '../types/apiModels'

export interface AssemblyTimeSearchForm {
  machine_model: string
  product_series: string
}

export interface AssemblyTimeFormModel {
  machine_model: string
  product_series: string
  assembly_name: string
  assembly_time_days: number
  production_sequence: number
  is_final_assembly: boolean
  is_default: boolean
  remark: string
}

const FINAL_ASSEMBLY_NAME = '整机总装'

const createDefaultSearchForm = (): AssemblyTimeSearchForm => ({
  machine_model: '',
  product_series: '',
})

const createDefaultForm = (): AssemblyTimeFormModel => ({
  machine_model: '',
  product_series: '',
  assembly_name: '',
  assembly_time_days: 1,
  production_sequence: 1,
  is_final_assembly: false,
  is_default: false,
  remark: '',
})

export const useAssemblyTimeConfigPage = () => {
  const searchForm = ref<AssemblyTimeSearchForm>(createDefaultSearchForm())

  const loading = ref(false)
  const tableData = ref<AssemblyTimeItem[]>([])
  const { sortField, sortOrder, handleSortChange, resetSort } = useTableSort()
  const sortedTableData = computed(() =>
    applyLocalSort(tableData.value, {
      sortField: sortField.value,
      sortOrder: sortOrder.value,
    }),
  )
  const {
    pageNo,
    pageSize,
    pageSizes,
    total,
    pagedData: pagedTableData,
    resetPagination,
  } = useLocalTablePagination(() => sortedTableData.value)

  const dialogVisible = ref(false)
  const isEdit = ref(false)
  const submitting = ref(false)
  const productionSequenceTouched = ref(false)
  const finalAssemblyRequestToken = ref(0)
  let finalAssemblySuggestTimer: ReturnType<typeof setTimeout> | null = null

  const form = ref<AssemblyTimeFormModel>(createDefaultForm())

  const rules: FormRules = {
    machine_model: [{ required: true, message: '请输入机床型号', trigger: 'blur' }],
    assembly_name: [{ required: true, message: '请输入装配名称', trigger: 'blur' }],
    assembly_time_days: [{ required: true, message: '请输入装配天数', trigger: 'blur' }],
    production_sequence: [{ required: true, message: '请输入生产顺序', trigger: 'blur' }],
  }

  const resetForm = () => {
    form.value = createDefaultForm()
    productionSequenceTouched.value = false
    finalAssemblyRequestToken.value += 1
    clearFinalAssemblySuggestTimer()
  }

  const handleAdd = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
  }

  const handleEdit = (row: AssemblyTimeItem) => {
    isEdit.value = true
    productionSequenceTouched.value = !(row.is_final_assembly || isWholeMachineFinalAssemblyName(row.assembly_name))
    finalAssemblyRequestToken.value += 1
    clearFinalAssemblySuggestTimer()
    form.value = {
      machine_model: row.machine_model,
      product_series: row.product_series || '',
      assembly_name: row.assembly_name,
      assembly_time_days: row.assembly_time_days,
      production_sequence: row.production_sequence,
      is_final_assembly: !!row.is_final_assembly,
      is_default: !!row.is_default,
      remark: row.remark || '',
    }
    dialogVisible.value = true
  }

  const handleDelete = async (row: AssemblyTimeItem) => {
    try {
      await showStructuredConfirmDialog({
        title: '删除确认',
        badge: '删除装配时长',
        headline: `确认删除【${row.machine_model} / ${row.assembly_name}】这条记录吗？`,
        description: '删除后该装配时长配置会立即从列表移除，后续需重新录入。',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }

    try {
      await request.delete(`/api/admin/assembly-times/${row.id}`)
      ElMessage.success('删除成功')
      await fetchData()
    } catch (error) {
      console.error(error)
    }
  }

  const clearFinalAssemblySuggestTimer = () => {
    if (finalAssemblySuggestTimer) {
      clearTimeout(finalAssemblySuggestTimer)
      finalAssemblySuggestTimer = null
    }
  }

  const isWholeMachineFinalAssemblyName = (assemblyName?: string | null) =>
    (assemblyName || '').trim() === FINAL_ASSEMBLY_NAME


  const normalizeFinalAssemblyForm = () => {
    if (isWholeMachineFinalAssemblyName(form.value.assembly_name)) {
      form.value.is_final_assembly = true
    }
  }

  const shouldSuggestFinalAssemblySequence = () =>
    dialogVisible.value &&
    form.value.is_final_assembly &&
    isWholeMachineFinalAssemblyName(form.value.assembly_name)

  const getSuggestedFinalAssemblySequence = async (machineModel: string) => {
    const rows = await request.get<AssemblyTimeItem[]>('/api/admin/assembly-times', {
      params: { machine_model: machineModel },
    })
    const items = Array.isArray(rows) ? rows : []
    const maxSequence = items.reduce((max, item) => {
      if (item.is_final_assembly || isWholeMachineFinalAssemblyName(item.assembly_name)) {
        return max
      }
      return Math.max(max, Number(item.production_sequence) || 0)
    }, 0)
    return maxSequence + 1
  }

  const scheduleFinalAssemblySequenceSuggestion = () => {
    clearFinalAssemblySuggestTimer()
    finalAssemblyRequestToken.value += 1

    if (productionSequenceTouched.value || !shouldSuggestFinalAssemblySequence()) {
      if (!productionSequenceTouched.value && !shouldSuggestFinalAssemblySequence()) {
        form.value.production_sequence = createDefaultForm().production_sequence
      }
      return
    }

    const machineModel = form.value.machine_model.trim()
    if (!machineModel) {
      form.value.production_sequence = createDefaultForm().production_sequence
      return
    }

    const requestToken = finalAssemblyRequestToken.value
    finalAssemblySuggestTimer = setTimeout(async () => {
      try {
        const nextSequence = await getSuggestedFinalAssemblySequence(machineModel)
        if (
          requestToken !== finalAssemblyRequestToken.value ||
          productionSequenceTouched.value ||
          !shouldSuggestFinalAssemblySequence() ||
          form.value.machine_model.trim() !== machineModel
        ) {
          return
        }
        form.value.production_sequence = nextSequence
      } catch (error) {
        if (requestToken === finalAssemblyRequestToken.value && !productionSequenceTouched.value) {
          form.value.production_sequence = createDefaultForm().production_sequence
        }
        console.error('Failed to suggest final assembly sequence', error)
      }
    }, 200)
  }

  const handleProductionSequenceChange = () => {
    productionSequenceTouched.value = true
  }

  const handleSubmit = async () => {
    normalizeFinalAssemblyForm()
    submitting.value = true
    try {
      await request.post('/api/admin/assembly-times', {
        machine_model: form.value.machine_model,
        product_series: form.value.product_series || null,
        assembly_name: form.value.assembly_name,
        assembly_time_days: form.value.assembly_time_days,
        production_sequence: form.value.production_sequence,
        is_final_assembly: form.value.is_final_assembly,
        is_default: form.value.is_default,
        remark: form.value.remark || null,
      })
      ElMessage.success(isEdit.value ? '编辑成功' : '新增成功')
      dialogVisible.value = false
      await fetchData()
    } catch (error) {
      console.error(error)
    } finally {
      submitting.value = false
    }
  }

  const fetchData = async () => {
    loading.value = true
    try {
      const res = await request.get<AssemblyTimeItem[]>('/api/admin/assembly-times', {
        params: cleanParams({ ...searchForm.value }),
      })
      tableData.value = Array.isArray(res) ? res : []
    } catch (error) {
      console.error(error)
    } finally {
      loading.value = false
    }
  }

  const handleSearch = () => {
    resetPagination()
    void fetchData()
  }

  const handleReset = () => {
    searchForm.value = createDefaultSearchForm()
    resetSort()
    resetPagination()
    handleSearch()
  }

  const handleTableSortChange = (sort: TableSortChange) => {
    handleSortChange(sort)
  }

  watch(
    () => [
      dialogVisible.value,
      isEdit.value,
      form.value.machine_model,
      form.value.assembly_name,
      form.value.is_final_assembly,
    ],
    () => {
      normalizeFinalAssemblyForm()
      scheduleFinalAssemblySequenceSuggestion()
    },
  )

  onMounted(() => {
    void fetchData()
  })

  return {
    searchForm,
    loading,
    pagedTableData,
    pageNo,
    pageSize,
    pageSizes,
    total,
    dialogVisible,
    isEdit,
    submitting,
    form,
    rules,
    handleAdd,
    handleEdit,
    handleDelete,
    handleSubmit,
    handleSearch,
    handleReset,
    handleTableSortChange,
    handleProductionSequenceChange,
  }
}




