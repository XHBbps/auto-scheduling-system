<template>
  <div class="tech-card p-6">
    <el-form :model="searchForm" inline class="flex flex-wrap gap-4">
      <el-form-item label="机床型号" class="!mb-0">
        <el-input :model-value="searchForm.machine_model" placeholder="请输入" clearable class="!w-48" @update:model-value="updateSearchForm({ machine_model: $event })" />
      </el-form-item>
      <el-form-item label="产品系列" class="!mb-0">
        <el-input :model-value="searchForm.product_series" placeholder="请输入" clearable class="!w-48" @update:model-value="updateSearchForm({ product_series: $event })" />
      </el-form-item>
      <el-form-item class="!mb-0 ml-auto">
        <el-button type="primary" @click="handleSearch" class="!px-6">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
        <el-button type="success" plain @click="handleAdd">新增</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { AssemblyTimeSearchForm } from '../../composables/useAssemblyTimeConfigPage'

const props = defineProps({
  searchForm: {
    type: Object as PropType<AssemblyTimeSearchForm>,
    required: true,
  },
  handleSearch: {
    type: Function as PropType<() => void>,
    required: true,
  },
  handleReset: {
    type: Function as PropType<() => void>,
    required: true,
  },
  handleAdd: {
    type: Function as PropType<() => void>,
    required: true,
  },
})

const emit = defineEmits<{
  (event: 'update:searchForm', value: AssemblyTimeSearchForm): void
}>()

const updateSearchForm = (patch: Partial<AssemblyTimeSearchForm>) => {
  emit('update:searchForm', { ...props.searchForm, ...patch })
}
</script>
