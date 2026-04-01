<template>
  <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
    <section class="summary-card summary-card--delivery">
      <div class="summary-card__header">
        <div class="summary-label">{{ labels.monthDelivery }}</div>
      </div>

      <div class="summary-metric-grid">
        <div class="summary-metric summary-metric--delivery-due">
          <span class="summary-metric__label">{{ '应交付' }}</span>
          <span class="summary-metric__value font-mono-num">{{ monthSummary.deliveryOrderCount }}</span>
          <span class="summary-metric__hint">
            {{ labels.orderUnit }} {{ monthSummary.deliveryOrderCount }} / {{ labels.quantityUnit }}
            {{ formatQuantity(monthSummary.deliveryQuantitySum) }}
          </span>
        </div>

        <div class="summary-metric summary-metric--placeholder">
          <span class="summary-metric__label">{{ '未交付' }}</span>
          <span class="summary-metric__value font-mono-num">--</span>
          <span class="summary-metric__hint">{{ '待数据补充' }}</span>
        </div>
      </div>
    </section>

    <section class="summary-card summary-card--planned-start">
      <div class="summary-card__header">
        <div class="summary-label">{{ labels.monthPlannedStart }}</div>
      </div>

      <div class="summary-metric-grid">
        <div class="summary-metric summary-metric--planned-start-due">
          <span class="summary-metric__label">{{ '应开工' }}</span>
          <span class="summary-metric__value font-mono-num">{{ monthSummary.plannedStartOrderCount }}</span>
          <span class="summary-metric__hint">
            {{ labels.orderUnit }} {{ monthSummary.plannedStartOrderCount }} / {{ labels.quantityUnit }}
            {{ formatQuantity(monthSummary.plannedStartQuantitySum) }}
          </span>
        </div>

        <div class="summary-metric summary-metric--placeholder">
          <span class="summary-metric__label">{{ '未开工' }}</span>
          <span class="summary-metric__value font-mono-num">--</span>
          <span class="summary-metric__hint">{{ '待数据补充' }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { WorkCalendarLabels, WorkCalendarMonthSummary } from '../../composables/useWorkCalendarPage'

defineProps({
  formatQuantity: {
    type: Function as PropType<(value?: string | number | null) => string>,
    required: true,
  },
  labels: {
    type: Object as PropType<WorkCalendarLabels>,
    required: true,
  },
  monthSummary: {
    type: Object as PropType<WorkCalendarMonthSummary>,
    required: true,
  },
})
</script>

<style scoped>
.summary-card {
  border-radius: 18px;
  border: 1px solid #2a2e2d;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.015) 100%),
    rgba(255, 255, 255, 0.02);
  padding: 18px 20px;
}

.summary-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.summary-label {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #717a82;
}

.summary-metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-metric {
  display: flex;
  min-height: 104px;
  flex-direction: column;
  gap: 8px;
  border-radius: 16px;
  border: 1px solid transparent;
  padding: 14px 14px 12px;
}

.summary-metric--delivery-due {
  border-color: rgba(56, 189, 248, 0.18);
  background: rgba(56, 189, 248, 0.1);
  color: #7dd3fc;
}

.summary-metric--planned-start-due {
  border-color: rgba(74, 222, 128, 0.18);
  background: rgba(74, 222, 128, 0.1);
  color: #86efac;
}

.summary-metric--placeholder {
  border-color: rgba(148, 163, 184, 0.12);
  background: rgba(255, 255, 255, 0.025);
  color: #a0aab2;
}

.summary-metric__label {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
}

.summary-metric__value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.summary-metric__hint {
  margin-top: auto;
  color: rgba(232, 234, 236, 0.88);
  line-height: 1.45;
  font-size: 12px;
}

.summary-metric--placeholder .summary-metric__hint {
  color: #8a949b;
}

@media (max-width: 768px) {
  .summary-card {
    padding: 16px;
  }

  .summary-metric-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .summary-metric {
    min-height: 88px;
    border-radius: 14px;
    padding: 12px;
  }

  .summary-metric__value {
    font-size: 24px;
  }
}
</style>
