<template>
  <div class="dashboard-header tech-card overflow-hidden p-6">
    <div class="dashboard-header__glow"></div>
    <div class="dashboard-header__content">
      <div class="dashboard-header__main">
        <div class="dashboard-header__eyebrow">Overview cockpit</div>
        <div class="dashboard-header__title-row">
          <div class="dashboard-header__icon-wrap">
            <el-icon :size="18"><TrendCharts /></el-icon>
          </div>
          <div>
            <div class="dashboard-header__title">排产总览</div>
            <div class="dashboard-header__subtitle">{{ currentModeDescription }}</div>
          </div>
        </div>
      </div>

      <div class="dashboard-header__side">
        <div class="dashboard-mode-switch" role="tablist" aria-label="排产视角切换">
          <button
            v-for="item in modeOptions"
            :key="item.value"
            type="button"
            class="dashboard-mode-switch__item"
            :class="{ 'dashboard-mode-switch__item--active': dashboardMode === item.value }"
            :aria-selected="dashboardMode === item.value"
            @click="dashboardModeModel = item.value"
          >
            <span class="dashboard-mode-switch__label">{{ item.label }}</span>
            <span class="dashboard-mode-switch__text">{{ item.description }}</span>
          </button>
        </div>

        <div class="dashboard-header__actions">
          <div class="dashboard-header__meta-pill">
            <span class="dashboard-header__meta-label">Data date</span>
            <span class="dashboard-header__meta-value">{{ todayLabel }}</span>
          </div>
          <button type="button" class="dashboard-header__reload" :disabled="loading" @click="$emit('reload')">
            {{ loading ? '刷新中...' : '刷新总览' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { TrendCharts } from '@element-plus/icons-vue'
import type { DashboardMode, DashboardModeOption } from '../../composables/useScheduleDashboardPage'

const props = defineProps({
  currentModeDescription: {
    type: String,
    required: true,
  },
  dashboardMode: {
    type: String as PropType<DashboardMode>,
    required: true,
  },
  loading: {
    type: Boolean,
    required: true,
  },
  modeOptions: {
    type: Array as PropType<DashboardModeOption[]>,
    required: true,
  },
  todayLabel: {
    type: String,
    required: true,
  },
})

const emit = defineEmits<{
  (event: 'update:dashboardMode', value: DashboardMode): void
  (event: 'reload'): void
}>()

const dashboardModeModel = computed({
  get: () => props.dashboardMode,
  set: (value) => emit('update:dashboardMode', value),
})
</script>

<style scoped>
.dashboard-header {
  position: relative;
  border-radius: 16px;
  background: #1a1d1c;
}

.dashboard-header__glow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top right, rgba(130, 214, 149, 0.08), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent 42%);
  opacity: 0.8;
  pointer-events: none;
}

.dashboard-header__content {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
  gap: 24px;
  align-items: stretch;
}

.dashboard-header__main {
  min-width: 0;
}

.dashboard-header__eyebrow {
  margin-bottom: 10px;
  color: #82d695;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  opacity: 0.88;
}

.dashboard-header__title-row {
  display: flex;
  gap: 14px;
  align-items: center;
}

.dashboard-header__icon-wrap {
  display: flex;
  width: 44px;
  height: 44px;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  border: 1px solid rgba(130, 214, 149, 0.12);
  background: rgba(130, 214, 149, 0.08);
  color: #82d695;
}

.dashboard-header__title {
  color: #ffffff;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.dashboard-header__subtitle {
  margin-top: 6px;
  max-width: 620px;
  color: #a0aab2;
  font-size: 13px;
  line-height: 1.7;
}

.dashboard-header__side {
  display: flex;
  flex-direction: column;
  gap: 14px;
  justify-content: space-between;
}

.dashboard-mode-switch {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dashboard-mode-switch__item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
  min-height: 88px;
  padding: 14px 16px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  background: #1e2120;
  text-align: left;
  color: #d4dde3;
  cursor: pointer;
  transition: border-color 160ms ease, background-color 160ms ease, transform 160ms ease;
}

.dashboard-mode-switch__item:hover {
  transform: translateY(-1px);
  border-color: rgba(130, 214, 149, 0.18);
}

.dashboard-mode-switch__item--active {
  border-color: rgba(130, 214, 149, 0.3);
  background: rgba(130, 214, 149, 0.08);
}

.dashboard-mode-switch__label {
  color: #ffffff;
  font-size: 15px;
  font-weight: 700;
}

.dashboard-mode-switch__text {
  color: #8f9ca4;
  font-size: 12px;
  line-height: 1.65;
}

.dashboard-header__actions {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.dashboard-header__meta-pill {
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  min-width: 144px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  background: #1e2120;
}

.dashboard-header__meta-label {
  color: #717a82;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.dashboard-header__meta-value {
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
}

.dashboard-header__reload {
  height: 40px;
  padding: 0 16px;
  border: 1px solid #2a2e2d;
  border-radius: 10px;
  background: #1e2120;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: 160ms ease;
}

.dashboard-header__reload:hover:not(:disabled) {
  border-color: #82d695;
  color: #82d695;
  background: #242827;
}

.dashboard-header__reload:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 1120px) {
  .dashboard-header__content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .dashboard-mode-switch {
    grid-template-columns: 1fr;
  }

  .dashboard-header__actions {
    justify-content: flex-start;
  }

  .dashboard-header__title {
    font-size: 22px;
  }
}
</style>
