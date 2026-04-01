import { reactive, ref } from 'vue'
import type { FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import request from '../utils/httpClient'
import type { MachineCycleItem } from './useMachineCycleBaselinePage'

export interface MachineCycleFormModel {
  machine_model: string
  product_series: string
  order_qty: number
  cycle_days_median: number
  sample_count: number
  is_active: boolean
  remark: string
}

const createDefaultForm = (): MachineCycleFormModel => ({
  machine_model: '',
  product_series: '',
  order_qty: 1,
  cycle_days_median: 30,
  sample_count: 0,
  is_active: true,
  remark: '',
})

export const useMachineCycleBaselineDialog = (options: { onSubmitted: () => Promise<void> }) => {
  const dialogVisible = ref(false)
  const isEdit = ref(false)
  const submitting = ref(false)
  const form = reactive<MachineCycleFormModel>(createDefaultForm())

  const rules: FormRules = {
    machine_model: [{ required: true, message: '请输入机床型号', trigger: 'blur' }],
    order_qty: [{ required: true, message: '请输入订单数量', trigger: 'blur' }],
    cycle_days_median: [{ required: true, message: '请输入周期天数', trigger: 'blur' }],
  }

  const resetForm = () => {
    Object.assign(form, createDefaultForm())
  }

  const handleAdd = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
  }

  const handleEdit = (row: MachineCycleItem) => {
    isEdit.value = true
    Object.assign(form, {
      machine_model: row.machine_model,
      product_series: row.product_series || '',
      order_qty: row.order_qty,
      cycle_days_median: row.cycle_days_median,
      sample_count: row.sample_count,
      is_active: row.is_active,
      remark: row.remark || '',
    })
    dialogVisible.value = true
  }

  const handleSubmit = async () => {
    submitting.value = true
    try {
      await request.post('/api/admin/machine-cycle-baselines', {
        machine_model: form.machine_model,
        product_series: form.product_series || null,
        order_qty: form.order_qty,
        cycle_days_median: form.cycle_days_median,
        sample_count: form.sample_count,
        is_active: form.is_active,
        remark: form.remark || null,
      })
      ElMessage.success(isEdit.value ? '编辑成功' : '新增成功')
      dialogVisible.value = false
      await options.onSubmitted()
    } catch (error) {
      console.error(error)
    } finally {
      submitting.value = false
    }
  }

  return {
    dialogVisible,
    isEdit,
    submitting,
    form,
    rules,
    handleAdd,
    handleEdit,
    handleSubmit,
  }
}
