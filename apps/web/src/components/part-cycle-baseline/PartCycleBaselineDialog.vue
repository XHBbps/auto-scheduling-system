<template>
  <el-dialog
    :model-value="visible"
    :title="isEdit ? '编辑零件周期基准' : '新增零件周期基准'"
    width="560px"
    destroy-on-close
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="零件类型" prop="part_type">
        <el-input v-model="form.part_type" placeholder="请输入" :disabled="isEdit" />
      </el-form-item>
      <el-form-item label="零件描述" prop="material_desc">
        <el-input v-model="form.material_desc" placeholder="请输入" />
      </el-form-item>
      <el-form-item label="机床型号" prop="machine_model">
        <el-input v-model="form.machine_model" placeholder="请输入" :disabled="isEdit" />
      </el-form-item>
      <el-form-item label="工厂">
        <el-input v-model="form.plant" placeholder="为空表示通用工厂基准" :disabled="isEdit" />
      </el-form-item>
      <el-form-item label="参考批量" prop="ref_batch_qty">
        <el-input-number v-model="form.ref_batch_qty" :min="0" :precision="2" :step="1" class="!w-full" />
      </el-form-item>
      <el-form-item label="周期天数" prop="cycle_days">
        <el-input-number v-model="form.cycle_days" :min="0" :precision="0" :step="1" class="!w-full" />
      </el-form-item>
      <el-form-item label="单件周期" prop="unit_cycle_days">
        <el-input-number v-model="form.unit_cycle_days" :min="0" :precision="1" :step="0.1" class="!w-full" />
      </el-form-item>
      <el-form-item label="匹配规则">
        <el-input v-model="form.match_rule" placeholder="选填" />
      </el-form-item>
      <el-form-item label="置信等级">
        <el-input v-model="form.confidence_level" placeholder="选填" />
      </el-form-item>
      <el-form-item label="是否启用">
        <el-switch v-model="form.is_active" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { PartCycleFormModel } from '../../composables/usePartCycleBaselineDialog'

const form = defineModel<PartCycleFormModel>('form', { required: true })

const props = defineProps<{
  visible: boolean
  isEdit: boolean
  submitting: boolean
  rules: FormRules
  onSubmit: () => void | Promise<void>
}>()

defineEmits<{
  'update:visible': [value: boolean]
}>()

const formRef = ref<FormInstance>()

const handleSubmit = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  await props.onSubmit()
}
</script>
