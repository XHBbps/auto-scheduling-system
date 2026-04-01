<template>
  <div class="tech-card p-8" data-test="dashboard-state-card" v-loading="loading">
    <div class="dashboard-state-card">
      <div class="dashboard-state-card__icon">
        <el-icon :size="24"><Warning /></el-icon>
      </div>
      <div class="space-y-3">
        <div class="text-lg font-semibold text-white" data-test="dashboard-state-title">
          {{ title }}
        </div>
        <div class="text-sm leading-6 text-text-muted" data-test="dashboard-state-message">
          {{ bodyText }}
        </div>
        <div class="flex flex-wrap items-center gap-3 pt-2">
          <el-button
            v-if="showRetryAction"
            type="primary"
            class="!rounded-lg"
            :loading="loading"
            @click="$emit('reload')"
          >
            重新加载
          </el-button>
          <el-button
            v-if="showLoginAction"
            type="primary"
            class="!rounded-lg"
            @click="$emit('go-login')"
          >
            前往登录
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Warning } from '@element-plus/icons-vue'

defineProps({
  bodyText: {
    type: String,
    required: true,
  },
  loading: {
    type: Boolean,
    required: true,
  },
  showLoginAction: {
    type: Boolean,
    required: true,
  },
  showRetryAction: {
    type: Boolean,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
})

defineEmits<{
  (event: 'go-login'): void
  (event: 'reload'): void
}>()
</script>
