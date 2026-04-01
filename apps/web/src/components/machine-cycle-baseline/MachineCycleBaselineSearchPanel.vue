<template>
  <div class="tech-card p-6">
    <el-form :model="searchForm" inline class="flex flex-wrap gap-4">
      <el-form-item label="机床型号" class="!mb-0">
        <el-input v-model="searchForm.machine_model" placeholder="请输入" clearable class="!w-48" />
      </el-form-item>
      <el-form-item label="产品系列" class="!mb-0">
        <el-input v-model="searchForm.product_series" placeholder="请输入" clearable class="!w-48" />
      </el-form-item>
      <el-form-item class="!mb-0 ml-auto">
        <el-button type="primary" class="!px-6" @click="onSearch">搜索</el-button>
        <el-button @click="onReset">重置</el-button>
        <el-button :loading="rebuilding" @click="onRebuild">重建基准</el-button>
        <el-button type="success" plain @click="onAdd">新增</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import type { MachineCycleSearchForm } from '../../composables/useMachineCycleBaselinePage'

const searchForm = defineModel<MachineCycleSearchForm>('searchForm', { required: true })

defineProps<{
  rebuilding: boolean
  onSearch: () => void | Promise<void>
  onReset: () => void | Promise<void>
  onRebuild: () => void | Promise<void>
  onAdd: () => void
}>()
</script>
