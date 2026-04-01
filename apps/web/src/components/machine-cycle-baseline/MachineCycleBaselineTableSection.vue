<template>
  <div class="tech-card p-6">
    <el-table
      v-loading="loading"
      :data="tableData"
      style="width: 100%"
      class="settings-table app-data-table"
      table-layout="fixed"
      @sort-change="onTableSortChange"
    >
      <template #empty>
        <AppTableState
          :state="tableFeedbackState"
          empty-text="暂无整机周期基准数据"
          error-action-text="重新加载"
          auth-action-text="前往登录"
          @action="onTableStateAction"
        />
      </template>

      <el-table-column prop="machine_model" label="机床型号" width="144" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-white font-medium">{{ row.machine_model }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="product_series" label="产品系列" width="120" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.product_series || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="order_qty" label="订单数量" width="96" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ row.order_qty }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="cycle_days_median" label="周期天数(中位数)" width="144" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-brand">{{ row.cycle_days_median }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="sample_count" label="样本数量" width="96" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ row.sample_count }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getActiveStatusBadgeMeta(row.is_active)" />
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-muted">{{ row.remark || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="144" fixed="right" align="center">
        <template #default="{ row }">
          <div class="flex items-center justify-center gap-3">
            <el-button link class="!text-brand hover:!text-brand/80" @click="onEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </div>
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
        @size-change="onFetchData"
        @current-change="onFetchData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppStatusBadge from '../AppStatusBadge.vue'
import AppTableState from '../AppTableState.vue'
import type { TableFeedbackState } from '../../composables/useTableFeedbackState'
import type { MachineCycleItem } from '../../composables/useMachineCycleBaselinePage'
import type { TableSortChange } from '../../composables/useTableSort'
import type { StatusBadgeMeta } from '../../utils/statusPresentation'

const pageNo = defineModel<number>('pageNo', { required: true })
const pageSize = defineModel<number>('pageSize', { required: true })

defineProps<{
  sortableColumnProps: Record<string, unknown>
  loading: boolean
  tableData: MachineCycleItem[]
  tableFeedbackState: TableFeedbackState
  pageSizes: readonly number[]
  total: number
  getActiveStatusBadgeMeta: (value?: boolean | null) => StatusBadgeMeta
  onEdit: (row: MachineCycleItem) => void
  onDelete: (row: MachineCycleItem) => void | Promise<void>
  onTableSortChange: (sort: TableSortChange) => void
  onTableStateAction: () => void | Promise<void>
  onFetchData: () => void | Promise<void>
}>()
</script>
