<template>
  <div class="space-y-6" v-loading="loading">
    <!-- 顶部导航 -->
    <div class="flex items-center gap-4">
      <el-button @click="router.back()" :icon="ArrowLeft" plain type="primary" class="!bg-transparent !border-none !text-text-secondary hover:!text-white">返回排产列表</el-button>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/schedules' }">排产列表</el-breadcrumb-item>
        <el-breadcrumb-item>排产详情 - <span class="text-white font-medium">{{ machineSchedule?.contract_no || '加载中...' }}</span></el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 订单基本信息 -->
    <div class="tech-card p-6">
      <div class="font-semibold text-white mb-6 flex items-center gap-2">
        <div class="w-1.5 h-4 bg-brand rounded-full"></div>
        订单基本信息
      </div>
      <el-descriptions :column="2" border class="tech-descriptions">
          <el-descriptions-item label="合同号">{{ machineSchedule?.contract_no }}</el-descriptions-item>
        <el-descriptions-item label="客户名称">{{ machineSchedule?.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="产品系列">{{ machineSchedule?.product_series }}</el-descriptions-item>
        <el-descriptions-item label="产品型号">{{ machineSchedule?.product_model }}</el-descriptions-item>
        <el-descriptions-item label="产品名称">{{ machineSchedule?.product_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="整机物料号">{{ machineSchedule?.material_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="数量">{{ machineSchedule?.quantity }}</el-descriptions-item>
        <el-descriptions-item label="订单类型">
          <AppStatusBadge v-bind="getOrderTypeBadgeMeta(machineSchedule?.order_type)" size="md" />
        </el-descriptions-item>
        <el-descriptions-item label="订单日期">
          <span class="font-mono-num">{{ formatDate(machineSchedule?.order_date) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="合同金额">{{ formatAmount(machineSchedule?.line_total_amount) }}</el-descriptions-item>
        <el-descriptions-item label="事业群">
          <AppStatusBadge v-bind="getBusinessGroupBadgeMeta(machineSchedule?.business_group)" size="md" />
        </el-descriptions-item>
        <el-descriptions-item label="定制号">{{ machineSchedule?.custom_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="销售人员">{{ machineSchedule?.sales_person_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="分公司">
          <AppStatusBadge v-bind="getSalesBranchCompanyBadgeMeta(machineSchedule?.sales_branch_company)" size="md" />
        </el-descriptions-item>
        <el-descriptions-item label="支公司">
          <AppStatusBadge v-bind="getSalesSubBranchBadgeMeta(machineSchedule?.sales_sub_branch)" size="md" />
        </el-descriptions-item>
          <el-descriptions-item label="销售订单">{{ machineSchedule?.order_no }}</el-descriptions-item>
        <el-descriptions-item label="SAP编码">{{ machineSchedule?.sap_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="SAP行号">{{ machineSchedule?.sap_line_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="确认交货期">
          <span class="font-mono-num">{{ formatDate(machineSchedule?.confirmed_delivery_date) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="图纸下发">
          <AppStatusBadge
            v-bind="getDrawingReleasedBadgeMeta(machineSchedule?.drawing_released)"
            size="md"
          />
          <span v-if="machineSchedule?.drawing_release_date" class="ml-2 text-text-muted font-mono-num text-sm">
            ({{ formatDate(machineSchedule?.drawing_release_date) }})
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="定制要求" :span="2">
          <div class="whitespace-pre-wrap break-words text-text-secondary">
            {{ machineSchedule?.custom_requirement || '-' }}
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="评审意见" :span="2">
          <div class="whitespace-pre-wrap break-words text-text-secondary">
            {{ machineSchedule?.review_comment || '-' }}
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 整机排产结果 -->
    <div class="tech-card p-6">
      <div class="font-semibold text-white mb-6 flex items-center gap-2">
        <div class="w-1.5 h-4 bg-brand rounded-full"></div>
        整机排产结果
      </div>
      
      <div class="flex items-center gap-4 mb-6">
        <AppStatusBadge
          v-bind="getScheduleStatusBadgeMeta(machineSchedule?.schedule_status)"
          size="md"
        />
        <AppStatusBadge
          v-bind="getWarningLevelBadgeMeta(machineSchedule?.warning_level)"
          size="md"
        />
        <div v-if="hasDefaultFlags" class="text-status-warning text-sm flex items-center gap-1 bg-status-warning/10 px-3 py-1 rounded-full">
          <el-icon><WarningFilled /></el-icon>
          部分数据使用默认值
        </div>
      </div>

      <el-descriptions :column="2" border class="tech-descriptions">
          <el-descriptions-item label="计划开工">
          <span class="font-mono-num font-bold text-white text-lg">{{ formatDate(machineSchedule?.planned_start_date) }}</span>
        </el-descriptions-item>
          <el-descriptions-item label="计划完工">
          <span class="font-mono-num font-bold text-brand text-lg">{{ formatDate(machineSchedule?.planned_end_date) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="触发日期">
          <span class="font-mono-num">{{ formatDate(machineSchedule?.trigger_date) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="整机周期(天)">
          <span class="font-mono-num">{{ machineSchedule?.machine_cycle_days ?? '-' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="整机装配(天)">
          <span class="font-mono-num">{{ machineSchedule?.machine_assembly_days ?? '-' }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 相关异常 -->
    <div v-if="issues.length > 0" class="tech-card p-6 border-status-danger border-opacity-30">
      <div class="font-semibold text-status-danger mb-6 flex items-center gap-2">
        <div class="w-1.5 h-4 bg-status-danger rounded-full"></div>
        相关异常 ({{ issues.length }})
      </div>
      <el-table :data="pagedIssues" style="width: 100%" @sort-change="handleIssueSortChange" class="app-data-table" table-layout="fixed">
        <el-table-column prop="issue_type" label="异常类型" width="120" v-bind="sortableColumnProps" />
        <el-table-column prop="issue_title" label="异常标题" width="200" v-bind="sortableColumnProps" />
        <el-table-column prop="issue_detail" label="异常详情" v-bind="sortableColumnProps" />
        <el-table-column prop="status" label="状态" width="100" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getIssueStatusBadgeMeta(row.status)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="mt-6 flex justify-end">
        <el-pagination
          v-model:current-page="issuePageNo"
          v-model:page-size="issuePageSize"
          :page-sizes="issuePageSizes"
          :total="issueTotal"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </div>

    <!-- 零件排产明细 -->
    <div class="tech-card p-6">
      <div class="flex items-center justify-between mb-6">
        <div class="font-semibold text-white flex items-center gap-2">
          <div class="w-1.5 h-4 bg-brand rounded-full"></div>
          零件排产明细
        </div>
        <el-button type="success" plain size="small" @click="handleExportParts" :loading="exporting" class="!rounded-lg">
          {{ exporting ? '导出中...' : '导出明细' }}
        </el-button>
      </div>
      <el-table :data="pagedPartSchedules" style="width: 100%" border @sort-change="handlePartSortChange" class="app-data-table" table-layout="fixed">
        <el-table-column prop="assembly_name" label="装配名称" width="120" v-bind="sortableColumnProps" />
        <el-table-column prop="part_name" label="自产件名称" min-width="160" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-text-secondary">{{ row.part_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="bom_path" label="完整路径" min-width="220" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-text-secondary">{{ row.bom_path || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="part_material_no" label="自产件料号" width="140" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-text-muted">{{ row.part_material_no || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="production_sequence" label="生产顺序" width="80" align="center" v-bind="sortableColumnProps" />
        <el-table-column prop="assembly_time_days" label="装配天数" width="80" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-text-secondary">{{ formatAssemblyDays(row.assembly_time_days) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="key_part_material_no" label="关键件料号" width="120" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-text-secondary">{{ row.key_part_material_no }}</span>
          </template>
        </el-table-column>
        <el-table-column label="关键件标识" width="96" align="center">
          <template #default="{ row }">
            <span
              class="inline-block h-3 w-3 rounded-full border"
              :class="row.is_key_part ? 'border-brand bg-brand' : 'border-text-secondary bg-transparent'"
            />
          </template>
        </el-table-column>
        <el-table-column prop="part_cycle_days" label="零件周期(天)" width="100" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num">{{ formatCycleDays(row.part_cycle_days) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="planned_start_date" label="计划开工" width="120" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-text-secondary">{{ formatDate(row.planned_start_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="planned_end_date" label="计划完工" width="120" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-text-secondary">{{ formatDate(row.planned_end_date) }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="mt-6 flex justify-end">
        <el-pagination
          v-model:current-page="partPageNo"
          v-model:page-size="partPageSize"
          :page-sizes="partPageSizes"
          :total="partTotal"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(.tech-descriptions .el-descriptions__label) {
  background-color: #1a1d1c !important;
  color: #717a82 !important;
  border-color: #2a2e2d !important;
  font-weight: 500;
}
:deep(.tech-descriptions .el-descriptions__content) {
  background-color: transparent !important;
  color: #ffffff !important;
  border-color: #2a2e2d !important;
}
</style>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useExportAction } from '../composables/useExportAction'
import { applyLocalSort, getTableSortColumnProps, useTableSort } from '../composables/useTableSort'
import { useLocalTablePagination } from '../composables/useTablePagination'
import { useRoute, useRouter } from 'vue-router'
import AppStatusBadge from '../components/AppStatusBadge.vue'
import request from '../utils/httpClient'
import { formatDate } from '../utils/format'
import { ArrowLeft, WarningFilled } from '@element-plus/icons-vue'
import {
  getBusinessGroupBadgeMeta,
  getDrawingReleasedBadgeMeta,
  getIssueStatusBadgeMeta,
  getOrderTypeBadgeMeta,
  getSalesBranchCompanyBadgeMeta,
  getSalesSubBranchBadgeMeta,
  getScheduleStatusBadgeMeta,
  getWarningLevelBadgeMeta,
} from '../utils/statusPresentation'
import type { MachineScheduleItem, PartScheduleItem, IssueItem, ScheduleDetailResponse } from '../types/apiModels'
const sortableColumnProps = getTableSortColumnProps()

const route = useRoute()
const router = useRouter()
const { exporting, runConfirmedExport } = useExportAction()
const orderLineId = computed(() => route.params.id)

const loading = ref(false)
const machineSchedule = ref<MachineScheduleItem | null>(null)
const partSchedules = ref<PartScheduleItem[]>([])
const issues = ref<IssueItem[]>([])
const { sortField: issueSortField, sortOrder: issueSortOrder, handleSortChange: handleIssueSortBaseChange } = useTableSort()
const {
  sortField: partSortField,
  sortOrder: partSortOrder,
  handleSortChange: handlePartSortBaseChange,
  buildSortParams: buildPartSortParams,
} = useTableSort()

const sortedIssues = computed(() => applyLocalSort(issues.value, { sortField: issueSortField.value, sortOrder: issueSortOrder.value }))
const sortedPartSchedules = computed(() => applyLocalSort(partSchedules.value, { sortField: partSortField.value, sortOrder: partSortOrder.value }))
const {
  pageNo: issuePageNo,
  pageSize: issuePageSize,
  pageSizes: issuePageSizes,
  total: issueTotal,
  pagedData: pagedIssues,
  resetPagination: resetIssuePagination,
} = useLocalTablePagination(() => sortedIssues.value)
const {
  pageNo: partPageNo,
  pageSize: partPageSize,
  pageSizes: partPageSizes,
  total: partTotal,
  pagedData: pagedPartSchedules,
  resetPagination: resetPartPagination,
} = useLocalTablePagination(() => sortedPartSchedules.value)

const hasDefaultFlags = computed(() => {
  if (!machineSchedule.value?.default_flags) return false
  return Object.keys(machineSchedule.value.default_flags).length > 0
})

const handleIssueSortChange = (sort: { prop?: string; order?: 'ascending' | 'descending' | null }) => {
  handleIssueSortBaseChange(sort)
}

const handlePartSortChange = (sort: { prop?: string; order?: 'ascending' | 'descending' | null }) => {
  handlePartSortBaseChange(sort)
}

const fetchData = async () => {
  if (!orderLineId.value) return
  loading.value = true
  resetIssuePagination()
  resetPartPagination()
  try {
    const res = await request.get<ScheduleDetailResponse>(`/api/schedules/${orderLineId.value}`)
    machineSchedule.value = res.machine_schedule || {}
    partSchedules.value = res.part_schedules || []
    issues.value = res.issues || []
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleExportParts = async () => {
  await runConfirmedExport({
    confirmTitle: '导出零件排产明细',
    confirmMessage: '确认导出当前整机订单的零件排产明细吗？系统将立即生成并开始下载文件。',
    fallbackFilename: `零件排产明细_${machineSchedule.value?.contract_no || Date.now()}.xlsx`,
    successMessage: '零件排产明细导出成功，已开始下载',
    failureMessage: '零件排产明细导出失败，请稍后重试',
    request: () =>
      request.get('/api/exports/part-schedules', {
        params: { order_line_id: orderLineId.value, ...buildPartSortParams() },
        responseType: 'blob',
        silentError: true,
      }),
  })
}

const formatCycleDays = (value?: number | string | null) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (Number.isNaN(num)) return value
  if (Number.isInteger(num)) return String(num)
  return num.toFixed(2).replace(/\.?0+$/, '')
}

const formatAssemblyDays = (value?: number | string | null) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (Number.isNaN(num)) return value
  return String(Math.trunc(num))
}

const formatAmount = (value?: number | string | null) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (Number.isNaN(num)) return String(value)
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(num)
}

onMounted(() => {
  fetchData()
})

watch(() => route.params.id, () => {
  fetchData()
})
</script>
