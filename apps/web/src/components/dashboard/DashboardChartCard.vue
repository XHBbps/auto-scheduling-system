<template>
  <div class="dashboard-chart-card tech-card" :class="`dashboard-chart-card--${panel.tone}`">
    <div class="dashboard-chart-card__header">
      <div class="dashboard-chart-card__header-main">
        <div class="dashboard-chart-card__icon" :class="`dashboard-chart-card__icon--${panel.tone}`">
          <el-icon :size="16"><component :is="panel.icon" /></el-icon>
        </div>
        <div>
          <div class="dashboard-chart-card__title">{{ panel.title }}</div>
          <div class="dashboard-chart-card__description">{{ panel.description }}</div>
        </div>
      </div>

      <div class="dashboard-chart-card__header-side">
        <div v-if="panel.actions?.length" class="dashboard-chart-card__actions">
          <button
            v-for="action in panel.actions"
            :key="`${panel.key}-${action.key}`"
            type="button"
            class="dashboard-chart-card__action"
            :class="{ 'dashboard-chart-card__action--active': action.active }"
            @click="triggerPanelAction(panel.key, action.key)"
          >
            {{ action.label }}
          </button>
        </div>
        <div class="dashboard-chart-card__stats">
          <div
            v-for="item in panel.stats"
            :key="`${panel.key}-${item.label}`"
            class="dashboard-chart-card__stat"
            :class="item.tone ? `dashboard-chart-card__stat--${item.tone}` : ''"
          >
            <span class="dashboard-chart-card__stat-label">{{ item.label }}</span>
            <span class="dashboard-chart-card__stat-value">{{ item.value }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="panel.hasData" :ref="bindChartRef" class="dashboard-chart-card__canvas"></div>
    <div v-else class="dashboard-chart-card__empty">{{ panel.emptyText }}</div>
  </div>
</template>

<script setup lang="ts">
import type { ComponentPublicInstance, PropType } from 'vue'
import type { DashboardChartPanel } from '../../composables/useScheduleDashboardPage'

const props = defineProps({
  panel: {
    type: Object as PropType<DashboardChartPanel>,
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

const bindChartRef = (ref: Element | ComponentPublicInstance | null) => {
  props.setChartRef(props.panel.key, ref as Element | null)
}
</script>

<style scoped>
.dashboard-chart-card {
  display: flex;
  min-height: 388px;
  flex-direction: column;
  padding: 24px;
  border-radius: 16px;
  background: #1a1d1c;
}

.dashboard-chart-card__header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.dashboard-chart-card__header-main {
  display: flex;
  gap: 12px;
  min-width: 0;
}

.dashboard-chart-card__header-side {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-end;
}

.dashboard-chart-card__icon {
  display: flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
}

.dashboard-chart-card__icon--success,
.dashboard-chart-card__icon--primary {
  color: #82d695;
}

.dashboard-chart-card__icon--cyan,
.dashboard-chart-card__icon--blue {
  color: #7fdfff;
}

.dashboard-chart-card__icon--warning,
.dashboard-chart-card__icon--orange {
  color: #ffd978;
}

.dashboard-chart-card__icon--danger {
  color: #ff8b8b;
}

.dashboard-chart-card__title {
  color: #ffffff;
  font-size: 16px;
  font-weight: 700;
}

.dashboard-chart-card__description {
  margin-top: 6px;
  color: #a0aab2;
  font-size: 13px;
  line-height: 1.7;
}

.dashboard-chart-card__actions {
  display: inline-flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.dashboard-chart-card__action {
  min-width: 42px;
  height: 30px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  background: #1e2120;
  color: #8f9ca4;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: 160ms ease;
}

.dashboard-chart-card__action:hover {
  border-color: rgba(130, 214, 149, 0.18);
  color: #dfe8ec;
}

.dashboard-chart-card__action--active {
  border-color: rgba(130, 214, 149, 0.3);
  background: rgba(130, 214, 149, 0.08);
  color: #82d695;
}

.dashboard-chart-card__stats {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.dashboard-chart-card__stat {
  display: inline-flex;
  flex-direction: column;
  gap: 3px;
  min-width: 80px;
  padding: 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  background: #1e2120;
}

.dashboard-chart-card__stat-label {
  color: #717a82;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.dashboard-chart-card__stat-value {
  color: #eaf3f7;
  font-size: 14px;
  font-weight: 700;
}

.dashboard-chart-card__stat--success .dashboard-chart-card__stat-value,
.dashboard-chart-card__stat--primary .dashboard-chart-card__stat-value {
  color: #82d695;
}

.dashboard-chart-card__stat--cyan .dashboard-chart-card__stat-value,
.dashboard-chart-card__stat--blue .dashboard-chart-card__stat-value {
  color: #7fdfff;
}

.dashboard-chart-card__stat--warning .dashboard-chart-card__stat-value,
.dashboard-chart-card__stat--orange .dashboard-chart-card__stat-value {
  color: #ffd978;
}

.dashboard-chart-card__stat--danger .dashboard-chart-card__stat-value {
  color: #ff8b8b;
}

.dashboard-chart-card__canvas {
  margin-top: 18px;
  min-height: 280px;
  flex: 1;
}

.dashboard-chart-card__empty {
  display: flex;
  min-height: 280px;
  flex: 1;
  align-items: center;
  justify-content: center;
  margin-top: 18px;
  color: #717a82;
  font-size: 13px;
  border-radius: 12px;
  border: 1px dashed rgba(255, 255, 255, 0.08);
  background: #1e2120;
}

@media (max-width: 1180px) {
  .dashboard-chart-card__header {
    flex-direction: column;
  }

  .dashboard-chart-card__header-side,
  .dashboard-chart-card__stats,
  .dashboard-chart-card__actions {
    align-items: flex-start;
    justify-content: flex-start;
  }
}
</style>
