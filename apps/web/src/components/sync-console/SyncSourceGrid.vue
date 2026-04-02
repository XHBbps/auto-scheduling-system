<template>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div v-for="source in props.syncSources" :key="source.title">
      <div class="sync-source-card tech-card p-6 h-full hover:border-brand/50 transition-colors duration-300 group">
        <div class="sync-source-card__body">
          <div class="sync-source-card__icon bg-surface-raised">
            <el-icon size="24" class="text-brand">
              <component :is="source.icon" />
            </el-icon>
          </div>

          <div class="sync-source-card__content">
            <div class="sync-source-card__header">
              <div class="font-semibold text-lg text-white">{{ source.title }}</div>
              <AppStatusBadge v-bind="props.getSyncViewStatusBadgeMeta(getSyncState(source.key).status)" />
            </div>

            <div class="text-text-muted text-sm leading-relaxed">{{ source.desc }}</div>
            <div v-if="props.getSyncStateDescription(source.key)" class="mt-2 text-xs text-text-muted">
              {{ props.getSyncStateDescription(source.key) }}
            </div>

            <div v-if="getSyncState(source.key).jobId" class="text-xs text-text-muted mt-3">
              任务 ID：{{ getSyncState(source.key).jobId }}
            </div>

            <div
              v-if="getSyncState(source.key).result || getSyncState(source.key).message"
              class="sync-source-card__result text-xs text-text-secondary mt-4 bg-surface-page p-3 rounded-lg border border-border"
            >
              <div v-if="getSyncState(source.key).result">
                成功 {{ getSyncState(source.key).result?.success_count ?? 0 }} 条；失败
                {{ getSyncState(source.key).result?.fail_count ?? 0 }} 条
              </div>
              <div
                v-if="getSyncState(source.key).message"
                class="mt-1"
                :class="{
                  'text-status-danger': getSyncState(source.key).status === 'error',
                  'text-status-warning': ['queued', 'running'].includes(getSyncState(source.key).status),
                  'text-brand': !['error', 'queued', 'running'].includes(getSyncState(source.key).status),
                }"
              >
                {{ getSyncState(source.key).message }}
              </div>
            </div>

            <div
              class="sync-source-card__footer"
              :class="source.key === 'bom' ? 'sync-source-card__footer--bom' : 'sync-source-card__footer--default'"
            >
              <div v-if="source.key === 'bom'" class="sync-source-card__bom-fields">
                <el-input
                  v-model="bomForm.material_no"
                  placeholder="请输入物料号"
                  clearable
                  size="small"
                  class="sync-source-card__bom-input sync-source-card__bom-input--material"
                />
                <el-input
                  v-model="bomForm.plant"
                  placeholder="请输入工厂"
                  clearable
                  size="small"
                  class="sync-source-card__bom-input sync-source-card__bom-input--plant"
                />
              </div>

              <el-button
                type="primary"
                plain
                size="small"
                class="sync-source-card__action !rounded-lg"
                :loading="getSyncState(source.key).triggering"
                :disabled="props.isSyncButtonDisabled(source.key)"
                @click="props.onHandleSync(source)"
              >
                {{ props.syncButtonLabel(source.key) }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppStatusBadge from '../AppStatusBadge.vue'
import type {
  SyncBomForm,
  SyncSource,
  SyncSourceKey,
  SyncStateItem,
  SyncViewStatus,
} from '../../composables/useSyncConsolePage'
import type { StatusBadgeMeta } from '../../utils/statusPresentation'

const props = defineProps<{
  getSyncStateDescription: (key: SyncSourceKey) => string
  getSyncViewStatusBadgeMeta: (value?: SyncViewStatus | null) => StatusBadgeMeta
  isSyncButtonDisabled: (key: SyncSourceKey) => boolean
  syncButtonLabel: (key: SyncSourceKey) => string
  syncSources: SyncSource[]
  syncState: Record<SyncSourceKey, SyncStateItem>
  onHandleSync: (source: SyncSource) => void | Promise<void>
}>()

const bomForm = defineModel<SyncBomForm>('bomForm', { required: true })

const getSyncState = (key: SyncSourceKey) => props.syncState[key]
</script>

<style scoped>
.sync-source-card {
  display: flex;
}

.sync-source-card__body {
  display: flex;
  align-items: flex-start;
  gap: 1.25rem;
  width: 100%;
  min-height: 100%;
}

.sync-source-card__icon {
  width: 3rem;
  height: 3rem;
  flex: 0 0 auto;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s ease;
}

.group:hover .sync-source-card__icon {
  transform: scale(1.1);
}

.sync-source-card__content {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  min-height: 100%;
}

.sync-source-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.sync-source-card__result {
  margin-bottom: 0;
}

.sync-source-card__footer {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  margin-top: auto;
  padding-top: 1.25rem;
}

.sync-source-card__footer--default {
  justify-content: flex-end;
}

.sync-source-card__footer--bom {
  justify-content: space-between;
  flex-wrap: wrap;
}

.sync-source-card__bom-fields {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
  flex: 1 1 18rem;
  min-width: 0;
  flex-wrap: wrap;
}

.sync-source-card__bom-input {
  flex: 0 0 auto;
}

.sync-source-card__bom-input--material {
  width: 10rem;
}

.sync-source-card__bom-input--plant {
  width: 7rem;
}

.sync-source-card__action {
  margin-left: auto;
  flex: 0 0 auto;
}

@media (max-width: 1280px) {
  .sync-source-card__footer--bom {
    align-items: stretch;
  }

  .sync-source-card__bom-fields {
    flex-basis: 100%;
  }
}
</style>
