<template>
  <div class="app-table-state">
    <div class="app-table-state__title">{{ resolvedTitle }}</div>
    <div class="app-table-state__text">{{ resolvedText }}</div>
    <button
      v-if="resolvedActionText"
      type="button"
      class="app-table-state__action"
      @click="$emit('action')"
    >
      {{ resolvedActionText }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TableFeedbackState } from '../composables/useTableFeedbackState'

const props = withDefaults(
  defineProps<{
    state?: TableFeedbackState
    title?: string
    text?: string
    emptyTitle?: string
    emptyText?: string
    loadingTitle?: string
    loadingText?: string
    errorTitle?: string
    errorText?: string
    authTitle?: string
    authText?: string
    forbiddenTitle?: string
    forbiddenText?: string
    disabledTitle?: string
    disabledText?: string
    actionText?: string
    errorActionText?: string
    authActionText?: string
    disabledActionText?: string
  }>(),
  {
    state: 'empty',
    title: '',
    text: '',
    emptyTitle: '暂无数据',
    emptyText: '当前筛选条件下暂无数据。',
    loadingTitle: '列表加载中',
    loadingText: '正在读取列表数据，请稍候。',
    errorTitle: '列表加载失败',
    errorText: '请稍后重试，或调整筛选条件后重新加载。',
    authTitle: '登录状态已失效',
    authText: '请重新登录后继续查看列表数据。',
    forbiddenTitle: '当前账号无权查看',
    forbiddenText: '请使用具备权限的账号访问当前列表。',
    disabledTitle: '当前列表暂不可用',
    disabledText: '请先完成前置条件后再查看列表。',
    actionText: '',
    errorActionText: '',
    authActionText: '',
    disabledActionText: '',
  },
)

defineEmits<{
  action: []
}>()

const resolvedTitle = computed(() => {
  if (props.title) return props.title
  if (props.state === 'loading') return props.loadingTitle
  if (props.state === 'error') return props.errorTitle
  if (props.state === 'auth') return props.authTitle
  if (props.state === 'forbidden') return props.forbiddenTitle
  if (props.state === 'disabled') return props.disabledTitle
  return props.emptyTitle
})

const resolvedText = computed(() => {
  if (props.text) return props.text
  if (props.state === 'loading') return props.loadingText
  if (props.state === 'error') return props.errorText
  if (props.state === 'auth') return props.authText
  if (props.state === 'forbidden') return props.forbiddenText
  if (props.state === 'disabled') return props.disabledText
  return props.emptyText
})

const resolvedActionText = computed(() => {
  if (props.actionText) return props.actionText
  if (props.state === 'error') return props.errorActionText
  if (props.state === 'auth') return props.authActionText
  if (props.state === 'disabled') return props.disabledActionText
  return ''
})
</script>

<style scoped>
.app-table-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 16px;
  text-align: center;
}

.app-table-state__title {
  color: #e5edf5;
  font-size: 15px;
  font-weight: 600;
}

.app-table-state__text {
  max-width: 560px;
  color: #8b98a2;
  font-size: 13px;
  line-height: 1.75;
}

.app-table-state__action {
  margin-top: 4px;
  padding: 0;
  border: none;
  background: transparent;
  color: #82d695;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.app-table-state__action:hover {
  color: #9be6ab;
}
</style>