<template>
  <div class="tech-card p-6">
    <div class="flex items-center justify-between mb-4">
      <div>
        <div class="text-white text-lg font-semibold">同步巡检概览</div>
        <div class="text-[#717a82] text-sm mt-1">聚合同步任务、快照与 BOM 补数队列的关键指标。</div>
        <div class="text-xs text-text-muted mt-2">最近刷新：{{ props.observabilityLastUpdatedAt }}</div>
      </div>
      <el-button
        plain
        class="!bg-transparent !border-[#2a2e2d] !text-[#a0aab2] hover:!text-brand hover:!border-brand"
        :loading="props.observabilityLoading"
        @click="props.onLoadSyncObservability"
      >
        刷新巡检
      </el-button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4 mb-6">
      <div
        v-for="metric in props.observabilityMetrics"
        :key="metric.label"
        class="rounded-xl border border-[#2a2e2d] bg-[#121413] p-4"
      >
        <div class="text-[11px] tracking-widest text-[#717a82] mb-2">{{ metric.label }}</div>
        <div class="text-2xl font-semibold font-mono-num" :class="metric.emphasis">{{ metric.value }}</div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-4 mb-6">
      <div
        v-for="metric in props.queueMetrics"
        :key="metric.label"
        class="rounded-xl border border-[#2a2e2d] bg-[#121413] p-4"
      >
        <div class="text-[11px] tracking-widest text-[#717a82] mb-2">{{ metric.label }}</div>
        <div class="text-2xl font-semibold font-mono-num" :class="metric.emphasis">{{ metric.value }}</div>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
      <div
        v-for="card in props.observabilityJobCards"
        :key="card.title"
        class="rounded-xl border border-[#2a2e2d] bg-[#121413] p-4"
      >
        <div class="flex items-center justify-between gap-3 mb-3">
          <div class="text-sm font-medium text-[#a0aab2]">{{ card.title }}</div>
          <AppStatusBadge
            v-if="card.job"
            v-bind="props.getSyncViewStatusBadgeMeta(props.jobViewStatus(card.job))"
          />
        </div>

        <template v-if="card.job">
          <div class="text-xs text-[#717a82] mb-2">
            开始时间：{{ props.formatRunTime(card.job.start_time) }}
            <span v-if="card.job.end_time"> · 结束时间：{{ props.formatRunTime(card.job.end_time) }}</span>
          </div>
          <div class="text-xs text-text-muted mb-3">
            {{ getJobStatusDescription(card.job) }}
          </div>
          <div class="flex flex-wrap gap-2 mb-3">
            <el-tag
              v-for="item in props.formatJobProgress(card.job)"
              :key="item"
              size="small"
              effect="dark"
              class="!border-none !bg-surface-page !text-text-secondary"
            >
              {{ item }}
            </el-tag>
          </div>
          <div class="rounded-lg border border-[#2a2e2d] bg-[#161918] px-3 py-2">
            <div class="text-[11px] tracking-widest text-[#717a82] mb-1">执行说明</div>
            <div class="text-xs text-text-secondary leading-6">{{ card.job.message || '暂无结果说明' }}</div>
          </div>
        </template>
        <div v-else class="text-sm text-[#717a82] py-6">暂无任务记录</div>
      </div>
    </div>

    <div class="mt-6 grid grid-cols-1 xl:grid-cols-2 gap-4">
      <div class="rounded-xl border border-[#2a2e2d] bg-[#121413] p-4">
        <div class="text-sm font-medium text-[#a0aab2] mb-3">失败类型分布</div>
        <div class="flex flex-wrap gap-2">
          <el-tag
            v-for="(count, key) in props.syncObservability.bom_backfill_queue.failure_kind_counts"
            :key="key"
            size="small"
            effect="dark"
            class="!border-none !bg-surface-page !text-text-secondary"
          >
            {{ props.failureKindLabelMap[key] || key }} {{ count }}
          </el-tag>
          <div
            v-if="!Object.keys(props.syncObservability.bom_backfill_queue.failure_kind_counts || {}).length"
            class="text-sm text-[#717a82]"
          >
            暂无失败类型数据
          </div>
        </div>
      </div>

      <div class="rounded-xl border border-[#2a2e2d] bg-[#121413] p-4">
        <div class="flex items-center justify-between gap-3 mb-3">
          <div>
            <div class="text-sm font-medium text-[#a0aab2]">最近失败 / 待重试物料</div>
            <div class="text-xs text-text-muted mt-1">失败记录可直接重试；待重试记录会展示下一次自动重试时间。</div>
          </div>
        </div>
        <div
          v-if="props.syncObservability.bom_backfill_queue.latest_failed_items.length"
          class="max-h-[252px] overflow-y-auto pr-1 sync-failed-items-scroll space-y-3"
        >
          <div
            v-for="item in props.syncObservability.bom_backfill_queue.latest_failed_items"
            :key="item.id"
            class="rounded-lg border border-[#2a2e2d] bg-surface-page p-3"
          >
            <div class="flex items-center justify-between gap-3 mb-2">
              <div class="text-sm text-white font-mono-num">{{ item.material_no }} / {{ item.plant }}</div>
              <AppStatusBadge v-bind="getQueueStatusBadgeMeta(item.status)" />
            </div>
            <div class="text-xs text-[#717a82] mb-1">
              {{ props.failureKindLabelMap[item.failure_kind || ''] || item.failure_kind || '未知类型' }}
              · 失败 {{ item.fail_count }} 次
            </div>
            <div class="text-xs text-text-secondary leading-6">{{ item.last_error || '暂无错误详情' }}</div>
            <div class="text-xs text-text-muted mt-2">{{ props.getQueueRetryHint(item) }}</div>
            <div class="mt-3 flex justify-end">
              <el-button
                v-if="props.canRetryBomBackfillItem(item)"
                size="small"
                plain
                class="!border-[#2a2e2d] !text-[#a0aab2] hover:!text-brand hover:!border-brand"
                :loading="Boolean(props.queueRetryingState[item.id])"
                @click="props.onRetryBomBackfillItem(item)"
              >
                立即重试
              </el-button>
            </div>
          </div>
        </div>
        <div v-else class="text-sm text-[#717a82] py-6">暂无失败记录</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppStatusBadge from '../AppStatusBadge.vue'
import { getQueueStatusBadgeMeta, type StatusBadgeMeta } from '../../utils/statusPresentation'
import type { BomBackfillQueueItem, SyncLogItem, SyncObservabilityResponse } from '../../types/apiModels'
import type { SyncMetricCard, SyncObservabilityJobCard, SyncViewStatus } from '../../composables/useSyncConsolePage'

const props = defineProps<{
  canRetryBomBackfillItem: (item: BomBackfillQueueItem) => boolean
  failureKindLabelMap: Record<string, string>
  formatJobProgress: (job?: SyncLogItem | null) => string[]
  formatRunTime: (value?: string | null) => string
  getQueueRetryHint: (item: BomBackfillQueueItem) => string
  getSyncViewStatusBadgeMeta: (value?: SyncViewStatus | null) => StatusBadgeMeta
  jobViewStatus: (job: SyncLogItem) => SyncViewStatus
  observabilityJobCards: SyncObservabilityJobCard[]
  observabilityLastUpdatedAt: string
  observabilityLoading: boolean
  observabilityMetrics: SyncMetricCard[]
  onRetryBomBackfillItem: (item: BomBackfillQueueItem) => void | Promise<void>
  queueMetrics: SyncMetricCard[]
  queueRetryingState: Record<number, boolean>
  syncObservability: SyncObservabilityResponse
  onLoadSyncObservability: () => void | Promise<void>
}>()

const getJobStatusDescription = (job: SyncLogItem) => {
  if (job.status === 'running') return '任务正在后台执行，请等待结果回写。'
  if (job.status === 'completed' && (job.fail_count ?? 0) === 0) return '任务已成功完成。'
  return '任务已结束，但包含失败记录或异常结果。'
}
</script>

<style scoped>
.sync-failed-items-scroll::-webkit-scrollbar {
  width: 4px;
}

.sync-failed-items-scroll::-webkit-scrollbar-thumb {
  background: #2a2e2d;
  border-radius: 9999px;
}

.sync-failed-items-scroll {
  scrollbar-color: #2a2e2d transparent;
  scrollbar-width: thin;
}
</style>
