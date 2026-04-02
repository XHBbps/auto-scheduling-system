<template>
  <div
    class="text-text-secondary text-sm bg-surface p-4 rounded-2xl border border-border flex items-center"
  >
    <el-icon class="mr-2 text-brand text-lg">
      <InfoFilled />
    </el-icon>
    此页面用于查看自动同步调度状态、手动触发同步任务，以及观察 BOM 补数队列与最近同步结果。
  </div>
</template>

<script setup lang="ts">
import { InfoFilled } from '@element-plus/icons-vue'
</script>
