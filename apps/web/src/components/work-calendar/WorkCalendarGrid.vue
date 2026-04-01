<template>
  <div class="tech-card p-6" v-loading="loading">
    <div class="calendar-grid">
      <div v-for="week in weekdayLabels" :key="week" class="weekday-cell">
        {{ week }}
      </div>

      <template v-for="cell in calendarCells" :key="cell.key">
        <div v-if="cell.empty" class="calendar-cell calendar-cell--empty"></div>
        <button
          v-else
          type="button"
          class="calendar-cell calendar-cell--active"
          :class="cell.isToday ? 'calendar-cell--today' : ''"
          @click="$emit('open-day-detail', cell.date)"
        >
          <div class="calendar-cell__header">
            <div class="font-mono-num text-lg font-semibold text-white">
              {{ cell.day }}
            </div>
            <div v-if="cell.isToday" class="today-badge">{{ labels.today }}</div>
          </div>

          <div class="calendar-cell__content">
            <div class="calendar-metric-grid">
              <div class="calendar-metric calendar-metric--delivery-due">
                <span class="calendar-metric__label">{{ '应交付' }}</span>
                <span class="calendar-metric__value font-mono-num">{{ cell.summary.delivery_order_count }}</span>
              </div>
              <div class="calendar-metric calendar-metric--placeholder">
                <span class="calendar-metric__label">{{ '未交付' }}</span>
                <span class="calendar-metric__value font-mono-num">--</span>
              </div>
              <div class="calendar-metric calendar-metric--planned-start-due">
                <span class="calendar-metric__label">{{ '应开工' }}</span>
                <span class="calendar-metric__value font-mono-num">{{ cell.summary.planned_start_order_count }}</span>
              </div>
              <div class="calendar-metric calendar-metric--placeholder">
                <span class="calendar-metric__label">{{ '未开工' }}</span>
                <span class="calendar-metric__value font-mono-num">--</span>
              </div>
            </div>
          </div>
        </button>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { WorkCalendarCell, WorkCalendarLabels } from '../../composables/useWorkCalendarPage'

defineProps({
  calendarCells: {
    type: Array as PropType<WorkCalendarCell[]>,
    required: true,
  },
  formatQuantity: {
    type: Function as PropType<(value?: string | number | null) => string>,
    required: true,
  },
  labels: {
    type: Object as PropType<WorkCalendarLabels>,
    required: true,
  },
  loading: {
    type: Boolean,
    required: true,
  },
  weekdayLabels: {
    type: Array as PropType<string[]>,
    required: true,
  },
})

defineEmits<{
  (e: 'open-day-detail', date: string): void
}>()
</script>

<style scoped>
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
}

.weekday-cell {
  padding-bottom: 4px;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  color: #717a82;
}

.calendar-cell {
  min-height: 110px;
  border-radius: 16px;
  border: 1px solid #2a2e2d;
  padding: 10px;
}

.calendar-cell--active {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.015) 100%),
    rgba(255, 255, 255, 0.02);
  color: #d7dce0;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.calendar-cell--active:hover {
  transform: translateY(-1px);
  border-color: rgba(130, 214, 149, 0.28);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.02) 100%),
    rgba(255, 255, 255, 0.03);
}

.calendar-cell--empty {
  min-height: 110px;
  border-radius: 16px;
  border: 1px dashed rgba(255, 255, 255, 0.04);
  background: rgba(255, 255, 255, 0.01);
}

.calendar-cell--today {
  box-shadow: inset 0 0 0 1px #82d695;
}

.calendar-cell__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.calendar-cell__content {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 10px;
}

.today-badge {
  border-radius: 9999px;
  background: rgba(130, 214, 149, 0.15);
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #82d695;
}

.calendar-metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 5px;
}

.calendar-metric {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 32px;
  border-radius: 10px;
  border: 1px solid transparent;
  padding: 6px 10px;
}

.calendar-metric--delivery-due {
  border-color: rgba(56, 189, 248, 0.18);
  background: rgba(56, 189, 248, 0.1);
  color: #7dd3fc;
}

.calendar-metric--planned-start-due {
  border-color: rgba(74, 222, 128, 0.18);
  background: rgba(74, 222, 128, 0.1);
  color: #86efac;
}

.calendar-metric--placeholder {
  border-color: rgba(148, 163, 184, 0.12);
  background: rgba(255, 255, 255, 0.025);
  color: #a0aab2;
}

.calendar-metric__label {
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
}

.calendar-metric__value {
  font-size: 15px;
  font-weight: 700;
  line-height: 1;
}

@media (max-width: 1024px) {
  .calendar-grid {
    gap: 10px;
  }

  .calendar-cell,
  .calendar-cell--empty {
    min-height: 100px;
    padding: 8px;
  }

  .calendar-metric {
    min-height: 28px;
    padding: 5px 8px;
  }
}

@media (max-width: 768px) {
  .calendar-grid {
    gap: 6px;
  }

  .calendar-cell,
  .calendar-cell--empty {
    min-height: 90px;
    border-radius: 12px;
    padding: 6px;
  }

  .weekday-cell {
    font-size: 12px;
  }

  .calendar-metric-grid {
    gap: 4px;
  }

  .calendar-metric {
    min-height: 26px;
    border-radius: 8px;
    padding: 4px 6px;
  }

  .calendar-metric__value {
    font-size: 14px;
  }
}
</style>
