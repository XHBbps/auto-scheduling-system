<template>
  <div class="dashboard-kpi-grid" data-test="dashboard-content">
    <div
      v-for="(card, index) in cards"
      :key="card.key"
      class="dashboard-kpi-card tech-card"
      :class="[
        `dashboard-kpi-card--${card.tone}`,
        cards.length === 7 && index < 3 ? 'dashboard-kpi-card--span-4' : '',
        cards.length === 7 && index >= 3 ? 'dashboard-kpi-card--span-3' : '',
      ]"
    >
      <div class="dashboard-kpi-card__header">
        <div>
          <div class="dashboard-kpi-card__title">{{ card.title }}</div>
          <div class="dashboard-kpi-card__value" :class="`dashboard-kpi-card__value--${card.tone}`">{{ card.value }}</div>
        </div>
        <div class="dashboard-kpi-card__icon" :class="`dashboard-kpi-card__icon--${card.tone}`">
          <el-icon :size="18"><component :is="card.icon" /></el-icon>
        </div>
      </div>
      <div class="dashboard-kpi-card__description">{{ card.description }}</div>
      <div class="dashboard-kpi-card__footnote">{{ card.footnote }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { DashboardCard } from '../../composables/useScheduleDashboardPage'

defineProps({
  cards: {
    type: Array as PropType<DashboardCard[]>,
    required: true,
  },
})
</script>

<style scoped>
.dashboard-kpi-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
}

.dashboard-kpi-card {
  grid-column: span 3 / span 3;
  padding: 20px;
  min-height: 168px;
  background: #1a1d1c;
}

.dashboard-kpi-card--span-4 {
  grid-column: span 4 / span 4;
}

.dashboard-kpi-card--span-3 {
  grid-column: span 3 / span 3;
}

.dashboard-kpi-card__header {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.dashboard-kpi-card__title {
  color: #8f9ca4;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.dashboard-kpi-card__value {
  margin-top: 14px;
  color: #ffffff;
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
}

.dashboard-kpi-card__icon {
  display: flex;
  width: 38px;
  height: 38px;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
}

.dashboard-kpi-card__description {
  margin-top: 16px;
  color: #a0aab2;
  font-size: 13px;
  line-height: 1.7;
  min-height: 44px;
}

.dashboard-kpi-card__footnote {
  margin-top: 14px;
  color: #717a82;
  font-size: 12px;
  line-height: 1.6;
}

.dashboard-kpi-card__value--success,
.dashboard-kpi-card__value--primary {
  color: #82d695;
}

.dashboard-kpi-card__value--warning,
.dashboard-kpi-card__value--orange {
  color: #ffd978;
}

.dashboard-kpi-card__value--danger {
  color: #ff8b8b;
}

.dashboard-kpi-card__value--blue,
.dashboard-kpi-card__value--info,
.dashboard-kpi-card__value--cyan {
  color: #7fdfff;
}

.dashboard-kpi-card__icon--success,
.dashboard-kpi-card__icon--primary {
  color: #82d695;
}

.dashboard-kpi-card__icon--warning,
.dashboard-kpi-card__icon--orange {
  color: #ffd978;
}

.dashboard-kpi-card__icon--danger {
  color: #ff8b8b;
}

.dashboard-kpi-card__icon--blue,
.dashboard-kpi-card__icon--info,
.dashboard-kpi-card__icon--cyan {
  color: #7fdfff;
}

@media (max-width: 1280px) {
  .dashboard-kpi-card,
  .dashboard-kpi-card--span-4,
  .dashboard-kpi-card--span-3 {
    grid-column: span 6 / span 6;
  }
}

@media (max-width: 760px) {
  .dashboard-kpi-card,
  .dashboard-kpi-card--span-4,
  .dashboard-kpi-card--span-3 {
    grid-column: span 12 / span 12;
  }
}
</style>
