<template>
  <el-dialog
    :model-value="visible"
    :title="isEdit ? '编辑装配时长' : '新增装配时长'"
    width="520px"
    destroy-on-close
    @update:model-value="emit('update:visible', $event)"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="机床型号" prop="machine_model">
        <el-input :model-value="form.machine_model" placeholder="请输入" :disabled="isEdit" @update:model-value="updateForm({ machine_model: $event })" />
      </el-form-item>
      <el-form-item label="产品系列" prop="product_series">
        <el-input :model-value="form.product_series" placeholder="请输入" @update:model-value="updateForm({ product_series: $event })" />
      </el-form-item>
      <el-form-item label="装配名称" prop="assembly_name">
        <el-input :model-value="form.assembly_name" placeholder="请输入" :disabled="isEdit" @update:model-value="updateForm({ assembly_name: $event })" />
      </el-form-item>
      <el-form-item label="装配天数" prop="assembly_time_days">
        <el-input-number :model-value="form.assembly_time_days" :min="0" :precision="2" :step="0.5" class="!w-full" @update:model-value="updateForm({ assembly_time_days: $event ?? 0 })" />
      </el-form-item>
      <el-form-item label="生产顺序" prop="production_sequence">
        <el-input-number
          :model-value="form.production_sequence"
          :min="1"
          :step="1"
          controls-position="right"
          class="!w-full"
          @update:model-value="updateForm({ production_sequence: $event ?? 1 })"
          @change="emit('production-sequence-change')"
        />
      </el-form-item>
      <el-form-item label="是否总装">
        <el-switch :model-value="form.is_final_assembly" @update:model-value="updateForm({ is_final_assembly: !!$event })" />
      </el-form-item>
      <el-form-item label="是否默认值">
        <el-switch :model-value="form.is_default" @update:model-value="updateForm({ is_default: !!$event })" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input :model-value="form.remark" type="textarea" :rows="2" placeholder="选填" @update:model-value="updateForm({ remark: $event })" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { PropType } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { AssemblyTimeFormModel } from '../../composables/useAssemblyTimeConfigPage'

const props = defineProps({
  visible: { type: Boolean, default: false },
  isEdit: { type: Boolean, default: false },
  submitting: { type: Boolean, default: false },
  form: {
    type: Object as PropType<AssemblyTimeFormModel>,
    required: true,
  },
  rules: {
    type: Object as PropType<FormRules>,
    required: true,
  },
})

const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'update:form', value: AssemblyTimeFormModel): void
  (event: 'submit'): void
  (event: 'production-sequence-change'): void
}>()

const formRef = ref<FormInstance>()

const updateForm = (patch: Partial<AssemblyTimeFormModel>) => {
  emit('update:form', { ...props.form, ...patch })
}

const handleConfirm = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  emit('submit')
}
</script>
