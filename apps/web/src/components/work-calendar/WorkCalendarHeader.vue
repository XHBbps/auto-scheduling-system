<template>
  <div class="tech-card p-6">
    <div class="flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
      <div class="space-y-3">
        <div class="flex items-center gap-2 text-white">
          <div class="h-4 w-1.5 rounded-full bg-brand"></div>
          <span class="text-lg font-semibold tracking-wide">{{ labels.title }}</span>
        </div>
        <div class="text-sm text-text-muted">
          {{ labels.subtitle }}
        </div>
        <div class="flex flex-wrap items-center gap-3 text-xs">
          <div class="legend-chip">
            <span class="legend-dot legend-dot--delivery"></span>
            <span>{{ labels.delivery }}</span>
          </div>
          <div class="legend-chip">
            <span class="legend-dot legend-dot--planned-start"></span>
            <span class="!text-[#86efac]">{{ labels.plannedStart }}</span>
          </div>
          <div class="legend-chip">
            <span class="legend-outline"></span>
            <span>{{ labels.today }}</span>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <div class="flex items-center gap-3 rounded-2xl border border-border bg-surface-overlay px-3 py-2">
          <el-button
            :icon="ArrowLeft"
            circle
            class="!border-none !bg-transparent !text-text-secondary hover:!bg-surface-raised hover:!text-white"
            @click="$emit('change-month', -1)"
          />
          <div class="min-w-[120px] text-center">
            <div class="text-xs uppercase tracking-[0.2em] text-text-muted">Month</div>
            <div class="font-mono-num text-xl font-semibold text-white">{{ currentMonthStr }}</div>
          </div>
          <el-button
            :icon="ArrowRight"
            circle
            class="!border-none !bg-transparent !text-text-secondary hover:!bg-surface-raised hover:!text-white"
            @click="$emit('change-month', 1)"
          />
        </div>

        <el-button
          plain
          class="!rounded-xl !border-border !bg-surface-overlay !text-text-secondary hover:!text-brand"
          @click="$emit('go-current-month')"
        >
          {{ labels.backToCurrentMonth }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import type { PropType } from 'vue'
import type { WorkCalendarLabels } from '../../composables/useWorkCalendarPage'

defineProps({
  currentMonthStr: {
    type: String,
    required: true,
  },
  labels: {
    type: Object as PropType<WorkCalendarLabels>,
    required: true,
  },
})

defineEmits<{
  (e: 'change-month', delta: number): void
  (e: 'go-current-month'): void
}>()
</script>

<style scoped>
.legend-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  padding: 6px 10px;
  color: #a0aab2;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
}

.legend-dot--delivery {
  background: rgba(56, 189, 248, 0.7);
}

.legend-dot--planned-start {
  background: rgba(74, 222, 128, 0.7);
}

.legend-outline {
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  border: 1px solid #82d695;
}
</style>
