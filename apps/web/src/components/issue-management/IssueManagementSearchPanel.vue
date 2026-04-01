<template>
  <div class="tech-card p-6">
    <el-form :model="searchForm" inline class="flex flex-wrap gap-4">
      <el-form-item label="异常类型" class="!mb-0">
        <el-select v-model="searchForm.issue_type" placeholder="请选择" clearable class="!w-48">
          <el-option v-for="t in issueTypeOptions" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" class="!mb-0">
        <el-select v-model="searchForm.status" placeholder="请选择" clearable class="!w-48">
          <el-option v-for="(val, key) in issueStatusMap" :key="key" :label="val.label" :value="key" />
        </el-select>
      </el-form-item>
      <el-form-item label="订单行ID" class="!mb-0">
        <el-input v-model="searchForm.bizKey" placeholder="请输入订单行ID" clearable class="!w-64" />
      </el-form-item>
      <el-form-item label="来源系统" class="!mb-0">
        <el-input v-model="searchForm.sourceSystem" placeholder="请输入" clearable class="!w-32" />
      </el-form-item>
      <el-form-item class="!mb-0 ml-auto">
        <el-button type="primary" @click="onHandleSearch" class="!px-6">搜索</el-button>
        <el-button @click="onHandleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import { ISSUE_STATUS_MAP } from '../../constants/enums'

const searchForm = defineModel<Record<string, string>>('searchForm', { required: true })

defineProps({
  issueTypeOptions: {
    type: Array as PropType<string[]>,
    required: true,
  },
  onHandleReset: {
    type: Function as PropType<() => void | Promise<void>>,
    required: true,
  },
  onHandleSearch: {
    type: Function as PropType<() => void | Promise<void>>,
    required: true,
  },
  issueStatusMap: {
    type: Object as PropType<typeof ISSUE_STATUS_MAP>,
    required: true,
  },
})
</script>
