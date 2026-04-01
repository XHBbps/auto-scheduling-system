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
      class="part-schedule-table app-data-table"
      table-layout="fixed"
      @sort-change="$emit('table-sort-change', $event)"
    >
      <template #empty>
        <AppTableState
          :state="tableFeedbackState"
          :empty-text="'暂无零件排产数据'"
          :error-text="'零件排产列表加载失败，请稍后重试。'"
          :auth-text="'当前登录状态已失效，请重新登录后查看零件排产列表。'"
          :forbidden-text="'当前账号没有查看零件排产列表的权限，请联系管理员。'"
          error-action-text="重新加载"
          auth-action-text="前往登录"
          @action="$emit('table-state-action')"
        />
      </template>

      <el-table-column prop="contract_no" label="合同号" width="136" fixed="left" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="cursor-pointer font-medium text-text-secondary hover:text-brand" @click="$emit('go-to-schedule-list', row)">
            {{ row.contract_no || '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="order_no" label="销售订单" width="136" fixed="left" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-muted">{{ row.order_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="assembly_name" label="装配名称" min-width="144" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.assembly_name || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="part_name" label="零件名称" min-width="240" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.part_name || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="bom_path" label="BOM路径" min-width="260" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.bom_path || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="part_material_no" label="零件料号" min-width="144" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-muted">{{ row.part_material_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="production_sequence" label="生产顺序" width="96" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ row.production_sequence }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="assembly_time_days" label="装配天数" width="96" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatAssemblyDays(row.assembly_time_days) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="part_cycle_days" label="零件周期" width="96" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatCycleDays(row.part_cycle_days) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="关键件" width="108" align="center">
        <template #default="{ row }">
          <span
            class="inline-block h-3 w-3 rounded-full border"
            :class="row.is_key_part ? 'border-brand bg-brand' : 'border-text-secondary bg-transparent'"
          />
        </template>
      </el-table-column>
      <el-table-column prop="planned_start_date" label="计划开工" width="132" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatDate(row.planned_start_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="planned_end_date" label="计划完工" width="132" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num font-medium text-text-secondary">{{ formatDate(row.planned_end_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="warning_level" label="异常标识" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getWarningLevelBadgeMeta(row.warning_level)" />
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('customer_name')" prop="customer_name" label="客户名称" min-width="180" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.customer_name || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('product_series')" prop="product_series" label="产品系列" width="120" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column v-if="isColumnVisible('product_model')" prop="product_model" label="产品型号" width="128" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.product_model || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('product_name')" prop="product_name" label="产品名称" min-width="180" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column v-if="isColumnVisible('material_no')" prop="material_no" label="整机物料号" min-width="144" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column v-if="isColumnVisible('order_type')" prop="order_type" label="订单类型" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getOrderTypeBadgeMeta(row.order_type)" />
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('custom_no')" prop="custom_no" label="定制号" width="120" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column v-if="isColumnVisible('business_group')" prop="business_group" label="事业群" width="120" align="center" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getBusinessGroupBadgeMeta(row.business_group)" />
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('sales_person_name')" prop="sales_person_name" label="销售人员" width="120" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column v-if="isColumnVisible('sales_branch_company')" prop="sales_branch_company" label="分公司" width="128" align="center" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getSalesBranchCompanyBadgeMeta(row.sales_branch_company)" />
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('sales_sub_branch')" prop="sales_sub_branch" label="支公司" width="128" align="center" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getSalesSubBranchBadgeMeta(row.sales_sub_branch)" />
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('order_date')" prop="order_date" label="订单日期" width="132" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatDate(row.order_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('confirmed_delivery_date')" prop="confirmed_delivery_date" label="确认交货期" width="132" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatDate(row.confirmed_delivery_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('line_total_amount')" prop="line_total_amount" label="合同金额" width="128" align="right" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatAmount(row.line_total_amount) }}</span>
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
import type { PartScheduleColumnOption, PartScheduleOptionalColumnKey } from '../../composables/usePartScheduleListPage'
import type { PartScheduleItem } from '../../types/apiModels'
import { formatDate } from '../../utils/format'
import {
  getBusinessGroupBadgeMeta,
  getOrderTypeBadgeMeta,
  getSalesBranchCompanyBadgeMeta,
  getSalesSubBranchBadgeMeta,
  getWarningLevelBadgeMeta,
} from '../../utils/statusPresentation'

const props = defineProps({
  formatAmount: {
    type: Function as PropType<(value?: number | string | null) => string>,
    required: true,
  },
  formatAssemblyDays: {
    type: Function as PropType<(value?: number | string | null) => string>,
    required: true,
  },
  formatCycleDays: {
    type: Function as PropType<(value?: number | string | null) => string>,
    required: true,
  },
  formatQuantity: {
    type: Function as PropType<(value?: number | string | null) => string>,
    required: true,
  },
  loading: {
    type: Boolean,
    required: true,
  },
  optionalColumns: {
    type: Array as PropType<PartScheduleColumnOption[]>,
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
  sortableColumnProps: {
    type: Object as PropType<Record<string, unknown>>,
    required: true,
  },
  tableData: {
    type: Array as PropType<PartScheduleItem[]>,
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
    type: Array as PropType<PartScheduleOptionalColumnKey[]>,
    required: true,
  },
})

const emit = defineEmits<{
  (event: 'fetch-data'): void
  (event: 'go-to-schedule-list', row: PartScheduleItem): void
  (event: 'reset-visible-columns'): void
  (event: 'table-sort-change', sort: { prop?: string; order?: 'ascending' | 'descending' | null }): void
  (event: 'table-state-action'): void
  (event: 'update:pageNo', value: number): void
  (event: 'update:pageSize', value: number): void
  (event: 'update:visibleColumnKeys', value: PartScheduleOptionalColumnKey[]): void
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

const isColumnVisible = (key: PartScheduleOptionalColumnKey) => props.visibleColumnKeys.includes(key)
</script>

