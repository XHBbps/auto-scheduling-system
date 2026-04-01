import { computed, onMounted, onUnmounted, reactive, ref, type Component } from 'vue'
import { ElMessage } from 'element-plus'
import { Box, DocumentCopy, ShoppingCart, TrendCharts } from '@element-plus/icons-vue'
import request from '../utils/httpClient'
import { showStructuredConfirmDialog } from '../utils/confirmDialog'
import { getSchedulerStateBadgeMeta } from '../utils/statusPresentation'
import type {
  BomBackfillQueueItem,
  PaginatedResponse,
  RetryQueueResponse,
  SyncLogItem,
  SyncObservabilityResponse,
  SyncOperationResult,
  SyncSchedulerStatus,
  SyncTriggerResponse,
} from '../types/apiModels'

export interface SyncSource {
  title: string
  key: SyncSourceKey
  icon: Component
  desc: string
  api: string
}

export interface SyncBomForm {
  material_no: string
  plant: string
}

export type SyncSourceKey = 'salesPlan' | 'bom' | 'productionOrders' | 'research'
export type SyncViewStatus = 'idle' | 'queued' | 'running' | 'success' | 'error' | 'noop'

export interface SyncStateItem {
  triggering: boolean
  status: SyncViewStatus
  result: SyncOperationResult | null
  jobId: number | null
  message: string
}

export interface SyncMetricCard {
  label: string
  value: string | number
  emphasis: string
}

export interface SyncObservabilityJobCard {
  title: string
  job: SyncLogItem | null
}

const DEFAULT_QUEUE_SUMMARY = {
  pending: 0,
  processing: 0,
  retry_wait: 0,
  success: 0,
  failed: 0,
  paused: 0,
  retry_wait_due: 0,
  failure_kind_counts: {},
  oldest_pending_age_minutes: null,
  latest_failed_items: [],
}

const JOB_POLL_INTERVAL_MS = 3000
const JOB_INITIAL_POLL_DELAY_MS = 1200
const ACTIVE_JOB_BOOTSTRAP_POLL_DELAY_MS = 1500
const OBSERVABILITY_REFRESH_MIN_INTERVAL_MS = 10000
const SCHEDULER_REFRESH_MIN_INTERVAL_MS = 15000
const SYNC_QUEUE_RETRYABLE_STATUSES = new Set(['retry_wait', 'failed'])

export const useSyncConsolePage = () => {
  const syncSources: SyncSource[] = [
    {
      title: '销售计划',
      key: 'salesPlan',
      icon: TrendCharts,
      desc: '从观远拉取销售计划数据，并触发图纸下发状态回填与自动补 BOM 入队。',
      api: '/api/admin/sync/sales-plan',
    },
    {
      title: 'BOM',
      key: 'bom',
      icon: Box,
      desc: '按物料号手动从 SAP 拉取 BOM 数据，适合单物料补数或联调验证。',
      api: '/api/admin/sync/bom',
    },
    {
      title: '生产订单',
      key: 'productionOrders',
      icon: ShoppingCart,
      desc: '从飞书生产订单表同步生产订单数据。',
      api: '/api/admin/sync/production-orders',
    },
    {
      title: '研究所数据',
      key: 'research',
      icon: DocumentCopy,
      desc: '从飞书研究所表同步图纸下发状态等数据，并触发周期基准重建与自动补 BOM 入队。',
      api: '/api/admin/sync/research',
    },
  ]

  const sourceKeyByJobType: Record<string, SyncSourceKey> = {
    sales_plan: 'salesPlan',
    bom: 'bom',
    production_order: 'productionOrders',
    research: 'research',
  }

  const schedulerJobNameMap: Record<string, string> = {
    sales_plan_sync: '销售计划同步',
    bom_sync: 'BOM 同步',
    bom_backfill_queue_consume: 'BOM 补数队列消费',
    production_order_sync: '生产订单同步',
    research_sync: '研究所数据同步',
    schedule_snapshot_reconcile: '排产快照对账刷新',
  }

  const failureKindLabelMap: Record<string, string> = {
    transient_error: '临时失败',
    empty_result: '空结果',
    permanent_error: '永久失败',
  }

  const bomForm = ref<SyncBomForm>({
    material_no: '',
    plant: '',
  })

  const createSyncState = (): SyncStateItem => ({
    triggering: false,
    status: 'idle',
    result: null,
    jobId: null,
    message: '',
  })

  const syncState = reactive<Record<SyncSourceKey, SyncStateItem>>({
    salesPlan: createSyncState(),
    bom: createSyncState(),
    productionOrders: createSyncState(),
    research: createSyncState(),
  })

  const pollTimers = new Map<SyncSourceKey, number>()
  const pollGeneration = new Map<SyncSourceKey, number>()
  let deferredObservabilityTimer: number | null = null
  let deferredSchedulerTimer: number | null = null
  let lastObservabilityRefreshAt = 0
  let lastSchedulerRefreshAt = 0
  const schedulerLastUpdatedAt = ref<string>('尚未刷新')
  const observabilityLastUpdatedAt = ref<string>('尚未刷新')
  const queueRetryingState = reactive<Record<number, boolean>>({})

  const schedulerLoading = ref(false)
  const schedulerRefreshing = ref(false)
  const schedulerEnabled = ref(false)
  const observabilityLoading = ref(false)

  const schedulerStatus = reactive<SyncSchedulerStatus>({
    enabled: false,
    state: 'paused',
    timezone: '--',
    jobs: [],
  })

  const syncObservability = reactive<SyncObservabilityResponse>({
    snapshot_total: 0,
    missing_bom_snapshot_count: 0,
    open_missing_bom_issue_count: 0,
    distinct_machine_bom_count: 0,
    running_job_count: 0,
    bom_backfill_queue: { ...DEFAULT_QUEUE_SUMMARY },
    latest_sales_plan_job: null,
    latest_research_job: null,
    latest_auto_bom_job: null,
  })

  const schedulerStateBadgeMeta = computed(() => getSchedulerStateBadgeMeta(schedulerStatus.state))

  const observabilityMetrics = computed<SyncMetricCard[]>(() => [
    { label: '快照总数', value: syncObservability.snapshot_total, emphasis: 'text-white' },
    { label: '缺 BOM 快照', value: syncObservability.missing_bom_snapshot_count, emphasis: 'text-status-warning' },
    { label: '未关闭 BOM 异常', value: syncObservability.open_missing_bom_issue_count, emphasis: 'text-status-danger' },
    { label: '整机 BOM 物料数', value: syncObservability.distinct_machine_bom_count, emphasis: 'text-brand' },
    { label: '执行中任务数', value: syncObservability.running_job_count, emphasis: 'text-brand' },
  ])

  const queueMetrics = computed<SyncMetricCard[]>(() => [
    { label: '待处理', value: syncObservability.bom_backfill_queue.pending, emphasis: 'text-white' },
    { label: '处理中', value: syncObservability.bom_backfill_queue.processing, emphasis: 'text-brand' },
    { label: '待重试', value: syncObservability.bom_backfill_queue.retry_wait, emphasis: 'text-status-warning' },
    { label: '永久失败', value: syncObservability.bom_backfill_queue.failed, emphasis: 'text-status-danger' },
    { label: '到期待重试', value: syncObservability.bom_backfill_queue.retry_wait_due, emphasis: 'text-status-warning' },
    {
      label: '最老待处理(分钟)',
      value: syncObservability.bom_backfill_queue.oldest_pending_age_minutes ?? '--',
      emphasis: 'text-white',
    },
  ])

  const observabilityJobCards = computed<SyncObservabilityJobCard[]>(() => [
    { title: '最新销售计划同步', job: syncObservability.latest_sales_plan_job ?? null },
    { title: '最新研究所同步', job: syncObservability.latest_research_job ?? null },
    { title: '最新自动补 BOM', job: syncObservability.latest_auto_bom_job ?? null },
  ])

  const jobViewStatus = (job: SyncLogItem): SyncViewStatus => {
    if (job.status === 'running') return 'running'
    if (job.status === 'completed' && (job.fail_count ?? 0) === 0) return 'success'
    return 'error'
  }

  const formatRunTime = (value?: string | null) => {
    if (!value) return '暂无计划时间'
    // 后端返回 UTC 时间，统一转换为北京时间展示
    const normalized = value.includes('T') && !value.endsWith('Z') ? `${value}Z` : value
    const date = new Date(normalized)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const markRefreshedAt = () =>
    new Date().toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })

  const formatJobProgress = (job?: SyncLogItem | null) => {
    const progress = job?.progress
    if (!progress) return []

    const items: string[] = []
    if (progress.batch_current && progress.batch_total) items.push(`批次 ${progress.batch_current}/${progress.batch_total}`)
    if (progress.candidate_orders !== undefined) items.push(`候选订单 ${progress.candidate_orders}`)
    if (progress.candidate_items !== undefined) items.push(`候选物料 ${progress.candidate_items}`)
    if (progress.enqueued_items !== undefined) items.push(`入队 ${progress.enqueued_items}`)
    if (progress.reactivated_items !== undefined) items.push(`重新激活 ${progress.reactivated_items}`)
    if (progress.already_tracked_items !== undefined) items.push(`已跟踪 ${progress.already_tracked_items}`)
    if (progress.processed_items !== undefined) items.push(`本轮处理 ${progress.processed_items}`)
    if (progress.retry_wait_items !== undefined) items.push(`待重试 ${progress.retry_wait_items}`)
    if (progress.failed_items !== undefined) items.push(`永久失败 ${progress.failed_items}`)
    if (progress.drawing_updated_count !== undefined) items.push(`图纸回填 ${progress.drawing_updated_count}`)
    if (progress.baseline_groups_processed !== undefined) items.push(`基准重建 ${progress.baseline_groups_processed}`)
    if (progress.refreshed_order_count !== undefined) items.push(`快照刷新 ${progress.refreshed_order_count}`)
    if (progress.closed_issue_count !== undefined) items.push(`异常收口 ${progress.closed_issue_count}`)
    return items
  }

  const applySchedulerStatus = (data: SyncSchedulerStatus) => {
    schedulerStatus.enabled = data.enabled
    schedulerStatus.state = data.state
    schedulerStatus.timezone = data.timezone
    schedulerStatus.jobs = data.jobs || []
    schedulerEnabled.value = data.enabled
  }

  const loadSchedulerStatus = async () => {
    schedulerRefreshing.value = true
    try {
      const res = await request.get<SyncSchedulerStatus>('/api/admin/sync/schedule')
      applySchedulerStatus(res)
      lastSchedulerRefreshAt = Date.now()
      schedulerLastUpdatedAt.value = markRefreshedAt()
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '未知错误'
      ElMessage.error(`获取调度状态失败：${message}`)
    } finally {
      schedulerRefreshing.value = false
    }
  }

  const loadSyncObservability = async (options?: { silent?: boolean }) => {
    observabilityLoading.value = !options?.silent
    try {
      const res = await request.get<SyncObservabilityResponse>('/api/admin/sync/observability', {
        silentError: true,
      })
      syncObservability.snapshot_total = res.snapshot_total ?? 0
      syncObservability.missing_bom_snapshot_count = res.missing_bom_snapshot_count ?? 0
      syncObservability.open_missing_bom_issue_count = res.open_missing_bom_issue_count ?? 0
      syncObservability.distinct_machine_bom_count = res.distinct_machine_bom_count ?? 0
      syncObservability.running_job_count = res.running_job_count ?? 0
      syncObservability.bom_backfill_queue = res.bom_backfill_queue || { ...DEFAULT_QUEUE_SUMMARY }
      syncObservability.latest_sales_plan_job = res.latest_sales_plan_job || null
      syncObservability.latest_research_job = res.latest_research_job || null
      syncObservability.latest_auto_bom_job = res.latest_auto_bom_job || null
      lastObservabilityRefreshAt = Date.now()
      observabilityLastUpdatedAt.value = markRefreshedAt()
    } catch (error) {
      console.error(error)
    } finally {
      observabilityLoading.value = false
    }
  }

  const clearDeferredObservabilityTimer = () => {
    if (deferredObservabilityTimer) {
      window.clearTimeout(deferredObservabilityTimer)
      deferredObservabilityTimer = null
    }
  }

  const clearDeferredSchedulerTimer = () => {
    if (deferredSchedulerTimer) {
      window.clearTimeout(deferredSchedulerTimer)
      deferredSchedulerTimer = null
    }
  }

  const refreshObservabilityThrottled = (config?: { immediate?: boolean; silent?: boolean }) => {
    const immediate = config?.immediate === true
    const silent = config?.silent !== false
    const now = Date.now()
    const waitMs = Math.max(0, OBSERVABILITY_REFRESH_MIN_INTERVAL_MS - (now - lastObservabilityRefreshAt))

    clearDeferredObservabilityTimer()

    if (immediate || waitMs === 0) {
      void loadSyncObservability({ silent })
      return
    }

    deferredObservabilityTimer = window.setTimeout(() => {
      deferredObservabilityTimer = null
      void loadSyncObservability({ silent })
    }, waitMs)
  }

  const refreshSchedulerStatusThrottled = (config?: { immediate?: boolean }) => {
    const immediate = config?.immediate === true
    const now = Date.now()
    const waitMs = Math.max(0, SCHEDULER_REFRESH_MIN_INTERVAL_MS - (now - lastSchedulerRefreshAt))

    clearDeferredSchedulerTimer()

    if (immediate || waitMs === 0) {
      void loadSchedulerStatus()
      return
    }

    deferredSchedulerTimer = window.setTimeout(() => {
      deferredSchedulerTimer = null
      void loadSchedulerStatus()
    }, waitMs)
  }

  const handleSchedulerToggle = async (value: string | number | boolean) => {
    schedulerLoading.value = true
    try {
      const res = await request.post<SyncSchedulerStatus>('/api/admin/sync/schedule', { enabled: Boolean(value) })
      applySchedulerStatus(res)
      ElMessage.success(Boolean(value) ? '已启用自动同步调度器' : '已暂停自动同步调度器')
    } catch (error: unknown) {
      schedulerEnabled.value = !Boolean(value)
      const message = error instanceof Error ? error.message : '未知错误'
      ElMessage.error(`切换调度状态失败：${message}`)
    } finally {
      schedulerLoading.value = false
    }
  }

  const clearPollTimer = (key: SyncSourceKey) => {
    const timer = pollTimers.get(key)
    if (timer) {
      window.clearTimeout(timer)
      pollTimers.delete(key)
    }
    // Bump generation to cancel any in-flight poll chain for this key
    pollGeneration.set(key, (pollGeneration.get(key) ?? 0) + 1)
  }

  const clearAllPollTimers = () => {
    ;(['salesPlan', 'bom', 'productionOrders', 'research'] as SyncSourceKey[]).forEach(clearPollTimer)
  }

  const applyJobResult = (key: SyncSourceKey, log: SyncLogItem) => {
    const state = syncState[key]
    state.jobId = log.id
    state.result = {
      success_count: log.success_count ?? 0,
      fail_count: log.fail_count ?? 0,
      message: log.message,
    }
    state.message = log.message || ''

    if (log.status === 'running') {
      state.status = 'running'
      return
    }

    state.status = log.status === 'completed' && (log.fail_count ?? 0) === 0 ? 'success' : 'error'
  }

  const pollJobStatus = async (key: SyncSourceKey, jobId: number, generation?: number) => {
    const gen = generation ?? (pollGeneration.get(key) ?? 0)
    try {
      const log = await request.get<SyncLogItem>(`/api/admin/sync-logs/${jobId}`, { silentError: true })

      // If generation changed while we were awaiting, another poll chain has taken over — bail out
      if ((pollGeneration.get(key) ?? 0) !== gen) return

      applyJobResult(key, log)

      if (log.status === 'running') {
        clearPollTimer(key)
        // Restore our generation since clearPollTimer bumped it
        pollGeneration.set(key, gen)
        pollTimers.set(key, window.setTimeout(() => void pollJobStatus(key, jobId, gen), JOB_POLL_INTERVAL_MS))
        return
      }

      clearPollTimer(key)
      if (syncState[key].status === 'success') {
        ElMessage.success(syncState[key].message || '同步已完成')
      } else {
        ElMessage.warning(syncState[key].message || '同步已结束，但存在失败或异常')
      }
      refreshObservabilityThrottled({ silent: true })
    } catch (error: unknown) {
      // Bail out if superseded
      if ((pollGeneration.get(key) ?? 0) !== gen) return
      clearPollTimer(key)
      syncState[key].status = 'error'
      syncState[key].message = error instanceof Error ? error.message : '查询任务状态失败'
    }
  }

  const loadActiveSyncJobs = async () => {
    try {
      const res = await request.get<PaginatedResponse<SyncLogItem>>('/api/admin/sync-logs', {
        params: { status: 'running', page_no: 1, page_size: 50 },
        silentError: true,
      })

      ;(res.items || []).forEach((item) => {
        const sourceKey = sourceKeyByJobType[item.job_type]
        if (!sourceKey) return
        applyJobResult(sourceKey, item)
        clearPollTimer(sourceKey)
        pollTimers.set(
          sourceKey,
          window.setTimeout(() => void pollJobStatus(sourceKey, item.id), ACTIVE_JOB_BOOTSTRAP_POLL_DELAY_MS),
        )
      })
    } catch (error) {
      console.error(error)
    }
  }

  const isSyncButtonDisabled = (key: SyncSourceKey) => {
    if (syncState[key].triggering || syncState[key].status === 'queued' || syncState[key].status === 'running') {
      return true
    }
    if (key === 'bom') return !bomForm.value.material_no || !bomForm.value.plant
    return false
  }

  const syncButtonLabel = (key: SyncSourceKey) => {
    if (syncState[key].triggering) return '触发中...'
    if (syncState[key].status === 'queued') return '已排队...'
    if (syncState[key].status === 'running') return '执行中...'
    if (syncState[key].status === 'error') return '重新同步'
    return '手动同步'
  }

  const getSyncStateDescription = (key: SyncSourceKey) => {
    const state = syncState[key]
    if (state.status === 'queued') return '任务已进入后台队列，等待 worker 认领执行。'
    if (state.status === 'running') return '任务正在后台执行，请等待结果回写。'
    if (state.status === 'success') return '最近一次同步已成功完成。'
    if (state.status === 'noop') return state.message || '当前数据状态无需重复执行同步。'
    if (state.status === 'error') return state.message || '最近一次同步存在失败或异常，请检查结果提示。'
    return ''
  }

  const canRetryBomBackfillItem = (item: BomBackfillQueueItem) =>
    Boolean(item?.id) && SYNC_QUEUE_RETRYABLE_STATUSES.has(item.status)

  const getQueueRetryHint = (item: BomBackfillQueueItem) => {
    if (item.status === 'retry_wait') {
      return item.next_retry_at
        ? `系统预计在 ${formatRunTime(item.next_retry_at)} 自动重试，也可立即手动重试。`
        : '当前记录处于待重试状态，也可立即手动重试。'
    }
    if (item.status === 'failed') {
      return '当前记录已进入永久失败状态，可手动重试重新入队。'
    }
    return '当前记录暂不支持手动重试。'
  }

  const handleRetryBomBackfillItem = async (item: BomBackfillQueueItem) => {
    if (!canRetryBomBackfillItem(item) || queueRetryingState[item.id]) {
      return
    }

    try {
      await showStructuredConfirmDialog({
        title: '重试 BOM 补数',
        headline: `确认立即重试 ${item.material_no} / ${item.plant}？`,
        description: getQueueRetryHint(item),
        confirmButtonText: '确认重试',
        cancelButtonText: '暂不处理',
        type: 'warning',
        customClass: 'app-confirm-message-box--sync',
      })
    } catch {
      return
    }

    queueRetryingState[item.id] = true
    try {
      const res = await request.post<RetryQueueResponse>('/api/admin/sync/bom-backfill-queue/retry', {
        ids: [item.id],
      })
      if (!res.updated_count) {
        ElMessage.warning(res.message || '当前记录暂未被重置，请刷新后重试。')
        return
      }
      ElMessage.success(res.message || '已将该记录重新加入待处理队列。')
      await loadSyncObservability({ silent: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '未知错误'
      ElMessage.error(`重试 BOM 补数失败：${message}`)
    } finally {
      queueRetryingState[item.id] = false
    }
  }

  const handleSync = async (source: SyncSource) => {
    try {
      await showStructuredConfirmDialog({
        title: '同步确认',
        headline: `确认立即执行 ${source.title} 同步？`,
        description:
          source.key === 'bom'
            ? '任务会按当前物料号与工厂条件进入后台队列执行，完成后页面将自动刷新最新状态。'
            : '任务会进入后台队列执行，完成后页面将自动刷新最新状态。',
        confirmButtonText: '确认同步',
        cancelButtonText: '暂不执行',
        type: 'warning',
        customClass: 'app-confirm-message-box--sync',
      })
    } catch {
      return
    }

    const state = syncState[source.key]
    state.result = null
    state.message = ''
    state.jobId = null

    let body: Record<string, string> = {}
    if (source.key === 'bom') {
      if (!bomForm.value.material_no || !bomForm.value.plant) {
        ElMessage.warning('请输入物料号和工厂后再执行 BOM 同步')
        return
      }
      body = {
        material_no: bomForm.value.material_no,
        plant: bomForm.value.plant,
      }
    }

    state.triggering = true
    try {
      const res = await request.post<SyncTriggerResponse>(source.api, body)
      state.message = res.message || ''

      if (res.status === 'noop' || !res.job_id) {
        state.status = 'noop'
        ElMessage.warning(res.message || '当前没有需要执行的同步任务')
        return
      }

      state.status = res.status === 'queued' ? 'queued' : 'running'
      state.jobId = res.job_id
      state.result = { success_count: 0, fail_count: 0, message: res.message }

      ElMessage.success(
        res.status === 'queued'
          ? res.message || `${source.title} 已进入后台队列`
          : res.message || `${source.title} 手动同步已触发`,
      )

      clearPollTimer(source.key)
      pollTimers.set(
        source.key,
        window.setTimeout(() => void pollJobStatus(source.key, res.job_id as number), JOB_INITIAL_POLL_DELAY_MS),
      )
      refreshSchedulerStatusThrottled()
      refreshObservabilityThrottled({ silent: true })
    } catch (error: unknown) {
      state.status = 'error'
      const message = error instanceof Error ? error.message : '未知错误'
      state.message = message
      ElMessage.error(`${source.title} 同步触发失败：${message}`)
    } finally {
      state.triggering = false
    }
  }

  onMounted(() => {
    refreshSchedulerStatusThrottled({ immediate: true })
    refreshObservabilityThrottled({ immediate: true, silent: false })
    void loadActiveSyncJobs()
  })

  onUnmounted(() => {
    clearAllPollTimers()
    clearDeferredObservabilityTimer()
    clearDeferredSchedulerTimer()
  })

  return {
    bomForm,
    failureKindLabelMap,
    formatJobProgress,
    formatRunTime,
    getSyncStateDescription,
    handleSchedulerToggle,
    handleSync,
    isSyncButtonDisabled,
    jobViewStatus,
    loadSchedulerStatus,
    loadSyncObservability,
    observabilityJobCards,
    observabilityLoading,
    observabilityLastUpdatedAt,
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
    canRetryBomBackfillItem,
    getQueueRetryHint,
    handleRetryBomBackfillItem,
  }
}
