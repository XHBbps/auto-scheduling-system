<template>
  <div class="h-full flex flex-col items-center justify-center text-center py-20">
    <div class="text-8xl font-bold text-brand/20 font-mono-num mb-4">404</div>
    <div class="text-xl text-white mb-2">页面不存在</div>
    <div class="text-text-muted mb-8">您访问的页面不存在或已被移除</div>
    <el-button type="primary" @click="router.push('/dashboard')">返回首页</el-button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>
