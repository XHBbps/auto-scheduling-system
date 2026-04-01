<template>
  <div class="dashboard-signals-grid">
    <div
      v-for="item in items"
      :key="item.key"
      class="dashboard-signal-card tech-card"
      :class="`dashboard-signal-card--${item.tone}`"
    >
      <div class="dashboard-signal-card__line"></div>
      <div class="dashboard-signal-card__title">{{ item.title }}</div>
      <div class="dashboard-signal-card__value">{{ item.value }}</div>
      <div class="dashboard-signal-card__description">{{ item.description }}</div>
      <button
        v-if="item.action && item.actionLabel"
        type="button"
        class="dashboard-signal-card__action"
        @click="item.action()"
      >
        {{ item.actionLabel }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { DashboardSignalCard } from '../../composables/useScheduleDashboardPage'

defineProps({
  items: {
    type: Array as PropType<DashboardSignalCard[]>,
    required: true,
  },
})
</script>

<style scoped>
.dashboard-signals-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.dashboard-signal-card {
  position: relative;
  min-height: 156px;
  padding: 18px 20px;
  border-radius: 16px;
  overflow: hidden;
}

.dashboard-signal-card__line {
  position: absolute;
  left: 0;
  top: 18px;
  bottom: 18px;
  width: 3px;
  border-radius: 999px;
  opacity: 0.85;
}

.dashboard-signal-card__title {
  color: #8f9ca4;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.dashboard-signal-card__value {
  margin-top: 12px;
  color: #ffffff;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.dashboard-signal-card__description {
  margin-top: 12px;
  color: #a0aab2;
  font-size: 13px;
  line-height: 1.7;
}

.dashboard-signal-card__action {
  margin-top: 14px;
  padding: 0;
  border: none;
  background: transparent;
  color: #82d695;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.dashboard-signal-card--success .dashboard-signal-card__line {
  background: #82d695;
}

.dashboard-signal-card--primary .dashboard-signal-card__line,
.dashboard-signal-card--cyan .dashboard-signal-card__line,
.dashboard-signal-card--blue .dashboard-signal-card__line {
  background: #7fdfff;
}

.dashboard-signal-card--warning .dashboard-signal-card__line,
.dashboard-signal-card--orange .dashboard-signal-card__line {
  background: #ffd978;
}

.dashboard-signal-card--danger .dashboard-signal-card__line {
  background: #ff8b8b;
}

@media (max-width: 1280px) {
  .dashboard-signals-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .dashboard-signals-grid {
    grid-template-columns: 1fr;
  }
}
</style>
