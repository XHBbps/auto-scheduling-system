<template>
  <el-dialog
    :model-value="visible"
    :title="isEdit ? '编辑整机周期基准' : '新增整机周期基准'"
    width="520px"
    destroy-on-close
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="机床型号" prop="machine_model">
        <el-input v-model="form.machine_model" placeholder="请输入" :disabled="isEdit" />
      </el-form-item>
      <el-form-item label="产品系列" prop="product_series">
        <el-input v-model="form.product_series" placeholder="请输入" />
      </el-form-item>
      <el-form-item label="订单数量" prop="order_qty">
        <el-input-number
          v-model="form.order_qty"
          :min="0"
          :precision="2"
          :step="1"
          class="!w-full"
          :disabled="isEdit"
        />
      </el-form-item>
      <el-form-item label="周期天数(中位数)" prop="cycle_days_median">
        <el-input-number v-model="form.cycle_days_median" :min="0" :precision="2" :step="1" class="!w-full" />
      </el-form-item>
      <el-form-item label="样本数量" prop="sample_count">
        <el-input-number v-model="form.sample_count" :min="0" :step="1" controls-position="right" class="!w-full" />
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
import type { MachineCycleFormModel } from '../../composables/useMachineCycleBaselineDialog'

const form = defineModel<MachineCycleFormModel>('form', { required: true })

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
