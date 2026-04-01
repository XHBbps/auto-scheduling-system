<template>
  <div class="dashboard-charts-grid">
    <DashboardChartCard
      v-for="panel in panels"
      :key="panel.key"
      class="dashboard-charts-grid__item"
      :class="`dashboard-charts-grid__item--span-${panel.span}`"
      :panel="panel"
      :set-chart-ref="setChartRef"
      :trigger-panel-action="triggerPanelAction"
    />
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import DashboardChartCard from './DashboardChartCard.vue'
import type { DashboardChartPanel } from '../../composables/useScheduleDashboardPage'

defineProps({
  panels: {
    type: Array as PropType<DashboardChartPanel[]>,
    required: true,
  },
  setChartRef: {
    type: Function as PropType<(key: string, element: Element | null) => void>,
    required: true,
  },
  triggerPanelAction: {
    type: Function as PropType<(panelKey: string, actionKey: string) => void>,
    required: true,
  },
})
</script>

<style scoped>
.dashboard-charts-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
}

.dashboard-charts-grid__item--span-4 {
  grid-column: span 4 / span 4;
}

.dashboard-charts-grid__item--span-6 {
  grid-column: span 6 / span 6;
}

.dashboard-charts-grid__item--span-8 {
  grid-column: span 8 / span 8;
}

.dashboard-charts-grid__item--span-12 {
  grid-column: span 12 / span 12;
}

@media (max-width: 960px) {
  .dashboard-charts-grid__item--span-4,
  .dashboard-charts-grid__item--span-6,
  .dashboard-charts-grid__item--span-8,
  .dashboard-charts-grid__item--span-12 {
    grid-column: span 12 / span 12;
  }
}
</style>
