<template>
  <div class="tech-card p-6">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div />
      <el-popover placement="bottom-end" :width="360" trigger="click">
        <template #reference>
          <el-button plain>显示列</el-button>
        </template>
        <div class="space-y-3">
          <div class="flex items-center justify-between gap-3">
            <div>
              <div class="text-sm font-medium text-text-primary">可选列配置</div>
              <div class="mt-1 text-xs text-text-muted">
                已显示 {{ visibleColumnKeys.length }}/{{ optionalColumns.length }} 个可选列
              </div>
            </div>
            <el-button link @click="$emit('reset-visible-columns')">恢复默认</el-button>
          </div>
          <el-checkbox-group v-model="visibleColumnKeysModel" class="grid grid-cols-2 gap-x-4 gap-y-2">
            <el-checkbox v-for="column in optionalColumns" :key="column.key" :value="column.key">
              {{ column.label }}
            </el-checkbox>
          </el-checkbox-group>
        </div>
      </el-popover>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      style="width: 100%"
      class="app-data-table"
      table-layout="fixed"
      @sort-change="$emit('table-sort-change', $event)"
    >
      <template #empty>
        <AppTableState
          :state="tableFeedbackState"
          :empty-text="'暂无整机排产数据'"
          :error-text="'整机排产列表加载失败，请稍后重试。'"
          :auth-text="'当前登录状态已失效，请重新登录后查看整机排产列表。'"
          :forbidden-text="'当前账号没有查看整机排产列表的权限，请联系管理员。'"
          error-action-text="重新加载"
          auth-action-text="前往登录"
          @action="$emit('table-state-action')"
        />
      </template>

      <el-table-column prop="contract_no" label="合同号" width="144" fixed="left" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="cursor-pointer font-medium text-white hover:text-brand" @click="$emit('go-detail', row)">
            {{ row.contract_no || '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="order_no" label="销售订单" width="144" fixed="left" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-muted">{{ row.order_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="customer_name" label="客户名称" min-width="180" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.customer_name || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="product_series" label="产品系列" width="120" v-bind="sortableColumnProps" />
      <el-table-column prop="product_model" label="产品型号" width="120" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.product_model || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column
        v-if="isColumnVisible('product_name')"
        prop="product_name"
        label="产品名称"
        width="180"
        show-overflow-tooltip
        v-bind="sortableColumnProps"
      />
      <el-table-column prop="material_no" label="物料号" width="136" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ row.material_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="quantity" label="数量" width="84" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatMachineQuantity(row.quantity) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="order_type" label="订单类型" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getOrderTypeBadgeMeta(row.order_type)" />
        </template>
      </el-table-column>
      <el-table-column
        v-if="isColumnVisible('custom_no')"
        prop="custom_no"
        label="定制号"
        width="120"
        show-overflow-tooltip
        v-bind="sortableColumnProps"
      />
      <el-table-column
        v-if="isColumnVisible('business_group')"
        prop="business_group"
        label="事业群"
        width="120"
        align="center"
        show-overflow-tooltip
        v-bind="sortableColumnProps"
      >
        <template #default="{ row }">
          <AppStatusBadge v-bind="getBusinessGroupBadgeMeta(row.business_group)" />
        </template>
      </el-table-column>
      <el-table-column
        v-if="isColumnVisible('sales_person_name')"
        prop="sales_person_name"
        label="销售人员"
        width="120"
        show-overflow-tooltip
        v-bind="sortableColumnProps"
      />
      <el-table-column
        v-if="isColumnVisible('sales_branch_company')"
        prop="sales_branch_company"
        label="分公司"
        width="128"
        align="center"
        show-overflow-tooltip
        v-bind="sortableColumnProps"
      >
        <template #default="{ row }">
          <AppStatusBadge v-bind="getSalesBranchCompanyBadgeMeta(row.sales_branch_company)" />
        </template>
      </el-table-column>
      <el-table-column
        v-if="isColumnVisible('sales_sub_branch')"
        prop="sales_sub_branch"
        label="支公司"
        width="128"
        align="center"
        show-overflow-tooltip
        v-bind="sortableColumnProps"
      >
        <template #default="{ row }">
          <AppStatusBadge v-bind="getSalesSubBranchBadgeMeta(row.sales_sub_branch)" />
        </template>
      </el-table-column>
      <el-table-column
        v-if="isColumnVisible('sap_code')"
        prop="sap_code"
        label="SAP编码"
        width="128"
        show-overflow-tooltip
        v-bind="sortableColumnProps"
      />
      <el-table-column
        v-if="isColumnVisible('sap_line_no')"
        prop="sap_line_no"
        label="SAP行号"
        width="112"
        show-overflow-tooltip
        v-bind="sortableColumnProps"
      />
      <el-table-column v-if="isColumnVisible('order_date')" prop="order_date" label="订单日期" width="132" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatDate(row.order_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="confirmed_delivery_date" label="确认交货期" width="132" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatDate(row.confirmed_delivery_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="drawing_released" label="图纸下发" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getDrawingReleasedBadgeMeta(row.drawing_released)" />
        </template>
      </el-table-column>
      <el-table-column prop="schedule_status" label="排产状态" width="128" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getScheduleStatusBadgeMeta(row.schedule_status)" />
        </template>
      </el-table-column>
      <el-table-column prop="planned_start_date" label="计划开工" width="132" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatDate(row.planned_start_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="planned_end_date" label="计划完工" width="132" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatDate(row.planned_end_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column
        v-if="isColumnVisible('line_total_amount')"
        prop="line_total_amount"
        label="合同金额"
        width="128"
        align="right"
        v-bind="sortableColumnProps"
      >
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatAmount(row.line_total_amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column
        v-if="isColumnVisible('custom_requirement')"
        prop="custom_requirement"
        label="定制要求"
        width="200"
        show-overflow-tooltip
        v-bind="sortableColumnProps"
      >
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.custom_requirement || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column
        v-if="isColumnVisible('review_comment')"
        prop="review_comment"
        label="评审意见"
        width="200"
        show-overflow-tooltip
        v-bind="sortableColumnProps"
      >
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.review_comment || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column
        v-if="isColumnVisible('warning_level')"
        prop="warning_level"
        label="异常标识"
        width="108"
        align="center"
        v-bind="sortableColumnProps"
      >
        <template #default="{ row }">
          <AppStatusBadge v-bind="getWarningLevelBadgeMeta(row.warning_level)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right" align="center">
        <template #default="{ row }">
          <el-tooltip :disabled="!getRunActionState(row).disabled" :content="getRunActionState(row).reason" placement="top">
            <span class="inline-flex">
              <el-button
                link
                class="!text-status-warning hover:!text-status-warning/80"
                :loading="partScheduleLoading[row.order_line_id]"
                :disabled="getRunActionState(row).disabled"
                @click="$emit('run-part-schedule', row)"
              >
                排产
              </el-button>
            </span>
          </el-tooltip>
          <el-divider direction="vertical" />
          <el-button link class="!text-brand hover:!text-brand/80" @click="$emit('go-detail', row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="mt-6 flex justify-end">
      <el-pagination
        v-model:current-page="pageNoModel"
        v-model:page-size="pageSizeModel"
        :page-sizes="pageSizes"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="$emit('fetch-data')"
        @current-change="$emit('fetch-data')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import AppStatusBadge from '../AppStatusBadge.vue'
import AppTableState from '../AppTableState.vue'
import type { TableFeedbackState } from '../../composables/useTableFeedbackState'
import type {
  MachineScheduleColumnOption,
  MachineScheduleOptionalColumnKey,
  MachineScheduleRunActionState,
} from '../../composables/useMachineScheduleListPage'
import type { MachineScheduleItem } from '../../types/apiModels'
import { formatDate } from '../../utils/format'
import {
  getBusinessGroupBadgeMeta,
  getDrawingReleasedBadgeMeta,
  getOrderTypeBadgeMeta,
  getSalesBranchCompanyBadgeMeta,
  getSalesSubBranchBadgeMeta,
  getScheduleStatusBadgeMeta,
  getWarningLevelBadgeMeta,
} from '../../utils/statusPresentation'

const props = defineProps({
  formatAmount: {
    type: Function as PropType<(value?: number | string | null) => string>,
    required: true,
  },
  formatMachineQuantity: {
    type: Function as PropType<(value?: number | string | null) => string>,
    required: true,
  },
  getRunActionState: {
    type: Function as PropType<(row: MachineScheduleItem) => MachineScheduleRunActionState>,
    required: true,
  },
  loading: {
    type: Boolean,
    required: true,
  },
  optionalColumns: {
    type: Array as PropType<MachineScheduleColumnOption[]>,
    required: true,
  },
  pageNo: {
    type: Number,
    required: true,
  },
  pageSize: {
    type: Number,
    required: true,
  },
  pageSizes: {
    type: Array as PropType<readonly number[]>,
    required: true,
  },
  partScheduleLoading: {
    type: Object as PropType<Record<number, boolean>>,
    required: true,
  },
  sortableColumnProps: {
    type: Object as PropType<Record<string, unknown>>,
    required: true,
  },
  tableData: {
    type: Array as PropType<MachineScheduleItem[]>,
    required: true,
  },
  tableFeedbackState: {
    type: String as PropType<TableFeedbackState>,
    required: true,
  },
  total: {
    type: Number,
    required: true,
  },
  visibleColumnKeys: {
    type: Array as PropType<MachineScheduleOptionalColumnKey[]>,
    required: true,
  },
})

const emit = defineEmits<{
  (event: 'fetch-data'): void
  (event: 'go-detail', row: MachineScheduleItem): void
  (event: 'reset-visible-columns'): void
  (event: 'run-part-schedule', row: MachineScheduleItem): void
  (event: 'table-sort-change', sort: { prop?: string; order?: 'ascending' | 'descending' | null }): void
  (event: 'table-state-action'): void
  (event: 'update:pageNo', value: number): void
  (event: 'update:pageSize', value: number): void
  (event: 'update:visibleColumnKeys', value: MachineScheduleOptionalColumnKey[]): void
}>()

const pageNoModel = computed({
  get: () => props.pageNo,
  set: (value) => emit('update:pageNo', value),
})

const pageSizeModel = computed({
  get: () => props.pageSize,
  set: (value) => emit('update:pageSize', value),
})

const visibleColumnKeysModel = computed({
  get: () => props.visibleColumnKeys,
  set: (value) => emit('update:visibleColumnKeys', value),
})

const isColumnVisible = (key: MachineScheduleOptionalColumnKey) => props.visibleColumnKeys.includes(key)
</script>

