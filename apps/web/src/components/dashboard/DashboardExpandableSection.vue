<template>
  <div v-if="hasContent" class="dashboard-expandable tech-card p-5">
    <button type="button" class="dashboard-expandable__toggle" @click="$emit('toggle')">
      <div>
        <div class="dashboard-expandable__title">{{ title }}</div>
        <div class="dashboard-expandable__description">{{ expanded ? '已展开补充指标与图表' : '展开后查看次级指标与补充图表' }}</div>
      </div>
      <span class="dashboard-expandable__action">{{ expanded ? '收起' : '展开查看' }}</span>
    </button>

    <div v-if="expanded" class="dashboard-expandable__content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  expanded: boolean
  hasContent: boolean
  title?: string
}>()

defineEmits<{
  (event: 'toggle'): void
}>()
</script>

<style scoped>
.dashboard-expandable {
  border-radius: 16px;
}

.dashboard-expandable__toggle {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.dashboard-expandable__title {
  color: #ffffff;
  font-size: 16px;
  font-weight: 700;
}

.dashboard-expandable__description {
  margin-top: 6px;
  color: #8f9ca4;
  font-size: 12px;
  line-height: 1.6;
}

.dashboard-expandable__action {
  color: #82d695;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.dashboard-expandable__content {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

@media (max-width: 720px) {
  .dashboard-expandable__toggle {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
