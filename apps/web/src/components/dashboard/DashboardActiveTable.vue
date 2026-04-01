<template>
  <div class="dashboard-table tech-card p-6">
    <div class="dashboard-table__header">
      <div>
        <div class="dashboard-table__title-row">
          <el-icon><List /></el-icon>
          <span>{{ title }}</span>
        </div>
        <div class="dashboard-table__description">{{ description }}</div>
      </div>
      <button type="button" class="dashboard-table__action" @click="$emit('view-all')">
        查看全部
      </button>
    </div>

    <el-table
      :data="rows"
      style="width: 100%"
      class="app-data-table"
      table-layout="fixed"
      @row-click="$emit('row-click', $event)"
      @sort-change="$emit('sort-change', $event)"
    >
      <template #empty>
        <AppTableState :text="emptyText" />
      </template>
      <el-table-column prop="contract_no" label="合同号" width="144" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="cursor-pointer font-medium text-white hover:text-brand">{{ row.contract_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="order_no" label="销售订单" width="144" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-muted">{{ row.order_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="customer_name" label="客户名称" min-width="170" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.customer_name || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="business_group" label="事业群" width="120" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.business_group || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="product_model" label="产品型号" width="120" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.product_model || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="quantity" label="数量" width="84" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatQuantity(row.quantity) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="confirmed_delivery_date" label="确认交货期" width="124" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatDate(row.confirmed_delivery_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="schedule_status" label="排产状态" width="120" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getScheduleStatusBadgeMeta(row.schedule_status)" />
        </template>
      </el-table-column>
      <el-table-column prop="warning_level" label="异常标识" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getWarningLevelBadgeMeta(row.warning_level)" />
        </template>
      </el-table-column>
      <el-table-column prop="planned_end_date" label="计划完工" width="124" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatDate(row.planned_end_date) }}</span>
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
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { List } from '@element-plus/icons-vue'
import AppStatusBadge from '../AppStatusBadge.vue'
import AppTableState from '../AppTableState.vue'
import type { MachineScheduleItem } from '../../types/apiModels'
import { formatDate } from '../../utils/format'
import { getScheduleStatusBadgeMeta, getWarningLevelBadgeMeta } from '../../utils/statusPresentation'

const props = defineProps({
  description: {
    type: String,
    required: true,
  },
  emptyText: {
    type: String,
    required: true,
  },
  formatQuantity: {
    type: Function as PropType<(value?: number | string | null) => string>,
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
  rows: {
    type: Array as PropType<MachineScheduleItem[]>,
    required: true,
  },
  sortableColumnProps: {
    type: Object as PropType<Record<string, unknown>>,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
  total: {
    type: Number,
    required: true,
  },
})

const emit = defineEmits<{
  (event: 'update:pageNo', value: number): void
  (event: 'update:pageSize', value: number): void
  (event: 'row-click', row: MachineScheduleItem): void
  (event: 'sort-change', sort: { prop?: string; order?: 'ascending' | 'descending' | null }): void
  (event: 'view-all'): void
}>()

const pageNoModel = computed({
  get: () => props.pageNo,
  set: (value) => emit('update:pageNo', value),
})

const pageSizeModel = computed({
  get: () => props.pageSize,
  set: (value) => emit('update:pageSize', value),
})
</script>

<style scoped>
.dashboard-table {
  border-radius: 16px;
}

.dashboard-table__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.dashboard-table__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ffffff;
  font-size: 18px;
  font-weight: 700;
}

.dashboard-table__description {
  margin-top: 8px;
  color: #a0aab2;
  font-size: 13px;
  line-height: 1.7;
}

.dashboard-table__action {
  height: 40px;
  padding: 0 16px;
  border: 1px solid #2a2e2d;
  border-radius: 10px;
  background: #1e2120;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.dashboard-table__action:hover {
  border-color: #82d695;
  color: #82d695;
  background: #242827;
}

@media (max-width: 720px) {
  .dashboard-table__header {
    flex-direction: column;
  }
}
</style>
