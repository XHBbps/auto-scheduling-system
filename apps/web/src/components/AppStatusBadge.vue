<template>
  <span class="app-status-badge" :class="[toneClass, sizeClass]" :title="badgeTitle" :style="badgeStyle">
    <span class="app-status-badge__dot" aria-hidden="true"></span>
    <span class="app-status-badge__text">{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StatusBadgeTone } from '../utils/statusPresentation'

const props = withDefaults(defineProps<{
  label: string
  tone?: StatusBadgeTone
  minWidth?: number | string
  title?: string
  size?: 'sm' | 'md'
}>(), {
  tone: 'neutral',
  minWidth: undefined,
  title: '',
  size: 'sm',
})

const toneClassMap: Record<StatusBadgeTone, string> = {
  success: 'app-status-badge--success',
  warning: 'app-status-badge--warning',
  danger: 'app-status-badge--danger',
  info: 'app-status-badge--info',
  primary: 'app-status-badge--primary',
  neutral: 'app-status-badge--neutral',
  cyan: 'app-status-badge--cyan',
  purple: 'app-status-badge--purple',
  orange: 'app-status-badge--orange',
  blue: 'app-status-badge--blue',
}

const toneClass = computed(() => toneClassMap[props.tone])
const sizeClass = computed(() => `app-status-badge--${props.size}`)
const badgeStyle = computed(() => {
  if (props.minWidth === undefined || props.minWidth === null || props.minWidth === '') {
    return undefined
  }
  return {
    minWidth: typeof props.minWidth === 'number' ? `${props.minWidth}px` : props.minWidth,
  }
})

const badgeTitle = computed(() => props.title || props.label)
</script>

<style scoped>
.app-status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  vertical-align: middle;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0;
  white-space: nowrap;
}

.app-status-badge__dot {
  width: 6px;
  height: 6px;
  flex: 0 0 6px;
  border-radius: 9999px;
  background: currentColor;
}

.app-status-badge__text {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: inherit;
}

.app-status-badge--sm {
  min-height: 18px;
  font-size: 12px;
  line-height: 18px;
}

.app-status-badge--md {
  min-height: 22px;
  font-size: 13px;
  line-height: 22px;
}

.app-status-badge--success {
  color: #86efac;
}

.app-status-badge--warning {
  color: #ffd978;
}

.app-status-badge--danger {
  color: #fca5a5;
}

.app-status-badge--info,
.app-status-badge--neutral {
  color: #cbd5e1;
}

.app-status-badge--primary {
  color: #82d695;
}

.app-status-badge--cyan {
  color: #6ef6ff;
}

.app-status-badge--purple {
  color: #d8b4fe;
}

.app-status-badge--orange {
  color: #fdba74;
}

.app-status-badge--blue {
  color: #93c5fd;
}
</style>
