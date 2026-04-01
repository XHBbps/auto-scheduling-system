<template>
  <div
    class="text-[#a0aab2] text-sm mb-6 bg-[#1a1d1c] p-4 rounded-xl border border-[#2a2e2d] flex items-center"
  >
    <el-icon class="mr-2 text-[#82d695] text-lg">
      <InfoFilled />
    </el-icon>
    此页面用于查看自动同步调度状态、手动触发同步任务，以及观察 BOM 补数队列与最近同步结果。
  </div>
</template>

<script setup lang="ts">
import { InfoFilled } from '@element-plus/icons-vue'
</script>
