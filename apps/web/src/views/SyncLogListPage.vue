<template>
  <div class="space-y-6">
    <div class="tech-card p-6">
      <el-form :model="searchForm" inline class="flex flex-wrap gap-4">
        <el-form-item label="任务类型" class="!mb-0">
          <el-select v-model="searchForm.jobType" placeholder="请选择" clearable class="!w-40">
            <el-option
              v-for="item in jobTypeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="来源系统" class="!mb-0">
          <el-select v-model="searchForm.sourceSystem" placeholder="请选择" clearable class="!w-40">
            <el-option label="观远" value="guandata" />
            <el-option label="SAP" value="sap" />
            <el-option label="飞书" value="feishu" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" class="!mb-0">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable class="!w-32">
            <el-option label="已完成" value="completed" />
            <el-option label="完成但有异常" value="completed_with_errors" />
            <el-option label="执行中" value="running" />
          </el-select>
        </el-form-item>
        <el-form-item class="!mb-0 ml-auto">
          <el-button type="primary" @click="handleSearch" class="!px-6">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="tech-card p-6">
      <div class="flex items-center justify-between mb-4">
        <div class="text-sm text-text-muted">执行中的任务会自动刷新</div>
        <el-button size="small" @click="refreshTable">刷新</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="tableData"
        :row-key="getRowKey"
        style="width: 100%"
        class="app-data-table"
        table-layout="fixed"
        @sort-change="handleTableSortChange"
      >
        <template #empty>
          <AppTableState
            :state="tableFeedbackState"
            :empty-text="'暂无同步日志'"
            error-action-text="重新加载"
            auth-action-text="前往登录"
            @action="handleTableStateAction"
          />
        </template>
        <el-table-column prop="job_type" label="任务类型" width="120" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-text-secondary">{{ jobTypeLabelMap[row.job_type] || row.job_type }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="source_system" label="来源系统" width="108" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-white font-medium">{{ sourceSystemLabelMap[row.source_system] || row.source_system }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="108" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getSyncJobStatusBadgeMeta(row.status)" />
          </template>
        </el-table-column>
        <el-table-column prop="success_count" label="成功数" width="96" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-brand">{{ row.success_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="fail_count" label="失败数" width="96" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num" :class="row.fail_count > 0 ? 'text-status-danger' : 'text-text-muted'">
              {{ row.fail_count }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="176" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-sm text-text-secondary">{{ formatDateTime(row.start_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="结束时间" width="176" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-sm text-text-muted">{{ formatDateTime(row.end_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" min-width="280" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-text-muted text-sm">{{ row.message || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="进度概览" min-width="300">
          <template #default="{ row }">
            <div
              v-if="getProgressSummaryChips(row).length"
              class="app-table-tag-strip"
              :title="getProgressSummaryText(row)"
            >
              <el-tag
                v-for="chip in getProgressSummaryChips(row)"
                :key="chip.key"
                size="small"
                effect="dark"
                class="!border-none !bg-surface-page !text-text-secondary"
              >
                {{ chip.label }}
              </el-tag>
            </div>
            <span v-else class="text-text-muted text-sm">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="88" fixed="right" align="center">
          <template #default="{ row }">
            <el-popconfirm title="确定删除此日志吗？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-end mt-6">
        <el-pagination
          v-model:current-page="pageNo"
          v-model:page-size="pageSize"
          :page-sizes="pageSizes"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="refreshTable"
          @current-change="refreshTable"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppStatusBadge from '../components/AppStatusBadge.vue'
import AppTableState from '../components/AppTableState.vue'
import { useRemoteTableQuery } from '../composables/useServerTableQuery'
import { createTableStateActionHandler } from '../composables/useTableFeedbackState'
import request from '../utils/httpClient'
import type { PaginatedResponse, SyncLogItem } from '../types/apiModels'
import { formatDateTime } from '../utils/format'
import { getSyncJobStatusBadgeMeta } from '../utils/statusPresentation'

const router = useRouter()
const route = useRoute()

const createSearchForm = () => ({ jobType: '', sourceSystem: '', status: '' })

const {
  sortableColumnProps,
  tableFeedbackState,
  loading,
  tableData,
  searchForm,
  pageNo,
  pageSize,
  pageSizes,
  total,
  fetchData,
  handleSearch,
  handleReset,
  handleTableSortChange,
} = useRemoteTableQuery({
  createSearchForm,
  perfScope: 'syncLogList',
  perfLabel: 'fetchSyncLogTable',
  buildPerfMeta: (params) => ({
    hasJobType: Boolean(params.job_type),
    hasSourceSystem: Boolean(params.source_system),
    hasStatus: Boolean(params.status),
  }),

  searchParamKeyMap: {
    jobType: 'job_type',
    sourceSystem: 'source_system',
  },
  sortFieldMap: {
    job_type: 'job_type',
    source_system: 'source_system',
    status: 'status',
    success_count: 'success_count',
    fail_count: 'fail_count',
    start_time: 'start_time',
    end_time: 'end_time',
    message: 'message',
  },
  request: (params) =>
    request.get<PaginatedResponse<SyncLogItem>>('/api/admin/sync-logs', {
      params,
      silentError: true,
    }),
})

let refreshTimer: number | null = null

const handleTableStateAction = createTableStateActionHandler({
  tableFeedbackState,
  retry: fetchData,
  router,
  redirectPath: route.fullPath,
})

const jobTypeLabelMap: Record<string, string> = {
  sales_plan: '销售计划',
  bom: 'BOM',
  production_order: '生产订单',
  research: '研究所数据',
  bom_backfill_queue: 'BOM补数消费',
  part_cycle_baseline: '零件周期基准重建',
}

const jobTypeOptions = [
  { value: 'sales_plan', label: jobTypeLabelMap.sales_plan },
  { value: 'bom', label: jobTypeLabelMap.bom },
  { value: 'production_order', label: jobTypeLabelMap.production_order },
  { value: 'research', label: jobTypeLabelMap.research },
  { value: 'bom_backfill_queue', label: jobTypeLabelMap.bom_backfill_queue },
  { value: 'part_cycle_baseline', label: jobTypeLabelMap.part_cycle_baseline },
]

const sourceSystemLabelMap: Record<string, string> = {
  guandata: '观远',
  sap: 'SAP',
  feishu: '飞书',
}

interface ProgressSummaryChip {
  key: string
  label: string
}

const getRowKey = (row: SyncLogItem) => row.id

const clearRefreshTimer = () => {
  if (refreshTimer) {
    window.clearTimeout(refreshTimer)
    refreshTimer = null
  }
}

const scheduleAutoRefresh = () => {
  clearRefreshTimer()
  const hasRunningJob = (tableData.value as SyncLogItem[]).some((item) => item.status === 'running')
  if (!hasRunningJob) return
  refreshTimer = window.setTimeout(() => {
    void fetchData({ silentLoading: true })
  }, 3000)
}

watch(
  tableData,
  () => {
    scheduleAutoRefresh()
  },
  { deep: true },
)

const formatProgressSummary = (item: SyncLogItem) => {
  const progress = item.progress
  if (!progress) return []

  const segments: string[] = []
  if (progress.batch_current && progress.batch_total) segments.push(`批次 ${progress.batch_current}/${progress.batch_total}`)
  if (progress.candidate_orders !== undefined) segments.push(`候选订单 ${progress.candidate_orders}`)
  if (progress.candidate_items !== undefined) segments.push(`候选物料 ${progress.candidate_items}`)
  if (progress.processed_items !== undefined) segments.push(`本轮处理 ${progress.processed_items}`)
  if (progress.deferred_items !== undefined) segments.push(`递延 ${progress.deferred_items}`)
  if (progress.drawing_updated_count !== undefined) segments.push(`图纸回填 ${progress.drawing_updated_count}`)
  if (progress.refreshed_order_count !== undefined) segments.push(`快照刷新 ${progress.refreshed_order_count}`)
  if (progress.closed_issue_count !== undefined) segments.push(`异常收口 ${progress.closed_issue_count}`)
  return segments
}

const getProgressSummaryChips = (item: SyncLogItem): ProgressSummaryChip[] =>
  formatProgressSummary(item).map((label, index) => ({
    key: `${item.id}-${index}-${label}`,
    label,
  }))

const getProgressSummaryText = (item: SyncLogItem) => formatProgressSummary(item).join(' | ')

const refreshTable = async () => {
  await fetchData()
}

const handleDelete = async (id: number) => {
  try {
    await request.delete(`/api/admin/sync-logs/${id}`)
    ElMessage.success('删除成功')
    await fetchData()
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  void fetchData()
})

onUnmounted(() => {
  clearRefreshTimer()
})
</script>
