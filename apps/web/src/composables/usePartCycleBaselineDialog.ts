import { reactive, ref } from 'vue'
import type { FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import request from '../utils/httpClient'
import { normalizePartCycleDays, normalizePartUnitCycleDays } from '../utils/partCyclePrecision'
import type { PartCycleItem } from './usePartCycleBaselinePage'

export interface PartCycleFormModel {
  id?: number
  part_type: string
  material_desc: string
  machine_model: string
  plant: string
  ref_batch_qty: number
  cycle_days: number
  unit_cycle_days: number
  match_rule: string
  confidence_level: string
  is_active: boolean
  remark: string
}

const createDefaultForm = (): PartCycleFormModel => ({
  id: undefined,
  part_type: '',
  material_desc: '',
  machine_model: '',
  plant: '',
  ref_batch_qty: 1,
  cycle_days: 30,
  unit_cycle_days: 1,
  match_rule: '',
  confidence_level: '',
  is_active: true,
  remark: '',
})

export const usePartCycleBaselineDialog = (options: {
  resolvePartType: (row: PartCycleItem) => string
  onSubmitted: () => Promise<void>
}) => {
  const dialogVisible = ref(false)
  const isEdit = ref(false)
  const submitting = ref(false)
  const form = reactive<PartCycleFormModel>(createDefaultForm())

  const rules: FormRules = {
    part_type: [{ required: true, message: '请输入零件类型', trigger: 'blur' }],
    material_desc: [{ required: true, message: '请输入零件描述', trigger: 'blur' }],
    machine_model: [{ required: true, message: '请输入机床型号', trigger: 'blur' }],
    ref_batch_qty: [{ required: true, message: '请输入参考批量', trigger: 'blur' }],
    cycle_days: [{ required: true, message: '请输入周期天数', trigger: 'blur' }],
    unit_cycle_days: [{ required: true, message: '请输入单件周期', trigger: 'blur' }],
  }

  const resetForm = () => {
    Object.assign(form, createDefaultForm())
  }

  const handleAdd = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
  }

  const handleEdit = (row: PartCycleItem) => {
    isEdit.value = true
    Object.assign(form, {
      id: row.id,
      part_type: options.resolvePartType(row),
      material_desc: row.material_desc,
      machine_model: row.machine_model || '',
      plant: row.plant || '',
      ref_batch_qty: row.ref_batch_qty,
      cycle_days: normalizePartCycleDays(row.cycle_days),
      unit_cycle_days: normalizePartUnitCycleDays(row.unit_cycle_days),
      match_rule: row.match_rule || '',
      confidence_level: row.confidence_level || '',
      is_active: row.is_active,
      remark: row.remark || '',
    })
    dialogVisible.value = true
  }

  const handleSubmit = async () => {
    submitting.value = true
    try {
      const normalizedCycleDays = normalizePartCycleDays(form.cycle_days)
      const normalizedUnitCycleDays = normalizePartUnitCycleDays(form.unit_cycle_days)
      form.cycle_days = normalizedCycleDays
      form.unit_cycle_days = normalizedUnitCycleDays

      await request.post('/api/admin/part-cycle-baselines', {
        id: form.id,
        part_type: form.part_type,
        material_desc: form.material_desc,
        machine_model: form.machine_model || null,
        plant: form.plant || null,
        ref_batch_qty: form.ref_batch_qty,
        cycle_days: normalizedCycleDays,
        unit_cycle_days: normalizedUnitCycleDays,
        match_rule: form.match_rule || null,
        confidence_level: form.confidence_level || null,
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
