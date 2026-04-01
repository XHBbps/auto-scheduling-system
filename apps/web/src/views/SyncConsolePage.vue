<template>
  <div class="space-y-6">
    <SyncConsoleIntro />

    <SyncSchedulerPanel
      v-model:scheduler-enabled="schedulerEnabled"
      :format-run-time="formatRunTime"
      :scheduler-job-name-map="schedulerJobNameMap"
      :scheduler-last-updated-at="schedulerLastUpdatedAt"
      :scheduler-loading="schedulerLoading"
      :scheduler-refreshing="schedulerRefreshing"
      :scheduler-state-badge-meta="schedulerStateBadgeMeta"
      :scheduler-status="schedulerStatus"
      :on-handle-scheduler-toggle="handleSchedulerToggle"
      :on-load-scheduler-status="loadSchedulerStatus"
    />

    <SyncObservabilityPanel
      :can-retry-bom-backfill-item="canRetryBomBackfillItem"
      :failure-kind-label-map="failureKindLabelMap"
      :format-job-progress="formatJobProgress"
      :format-run-time="formatRunTime"
      :get-queue-retry-hint="getQueueRetryHint"
      :get-sync-view-status-badge-meta="getSyncViewStatusBadgeMeta"
      :job-view-status="jobViewStatus"
      :observability-job-cards="observabilityJobCards"
      :observability-last-updated-at="observabilityLastUpdatedAt"
      :observability-loading="observabilityLoading"
      :observability-metrics="observabilityMetrics"
      :on-retry-bom-backfill-item="handleRetryBomBackfillItem"
      :queue-metrics="queueMetrics"
      :queue-retrying-state="queueRetryingState"
      :sync-observability="syncObservability"
      :on-load-sync-observability="loadSyncObservability"
    />

    <SyncSourceGrid
      v-model:bom-form="bomForm"
      :get-sync-state-description="getSyncStateDescription"
      :get-sync-view-status-badge-meta="getSyncViewStatusBadgeMeta"
      :is-sync-button-disabled="isSyncButtonDisabled"
      :sync-button-label="syncButtonLabel"
      :sync-sources="syncSources"
      :sync-state="syncState"
      :on-handle-sync="handleSync"
    />
  </div>
</template>

<script setup lang="ts">
import SyncConsoleIntro from '../components/sync-console/SyncConsoleIntro.vue'
import SyncObservabilityPanel from '../components/sync-console/SyncObservabilityPanel.vue'
import SyncSchedulerPanel from '../components/sync-console/SyncSchedulerPanel.vue'
import SyncSourceGrid from '../components/sync-console/SyncSourceGrid.vue'
import { useSyncConsolePage } from '../composables/useSyncConsolePage'
import { getSyncViewStatusBadgeMeta } from '../utils/statusPresentation'

const {
  bomForm,
  canRetryBomBackfillItem,
  failureKindLabelMap,
  formatJobProgress,
  formatRunTime,
  getQueueRetryHint,
  getSyncStateDescription,
  handleRetryBomBackfillItem,
  handleSchedulerToggle,
  handleSync,
  isSyncButtonDisabled,
  jobViewStatus,
  loadSchedulerStatus,
  loadSyncObservability,
  observabilityJobCards,
  observabilityLastUpdatedAt,
  observabilityLoading,
  observabilityMetrics,
  queueMetrics,
  queueRetryingState,
  schedulerEnabled,
  schedulerJobNameMap,
  schedulerLastUpdatedAt,
  schedulerLoading,
  schedulerRefreshing,
  schedulerStateBadgeMeta,
  schedulerStatus,
  syncButtonLabel,
  syncObservability,
  syncSources,
  syncState,
} = useSyncConsolePage()
</script>

