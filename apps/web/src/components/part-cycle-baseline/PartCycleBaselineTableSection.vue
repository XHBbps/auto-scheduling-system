<template>
  <div class="tech-card p-6">
    <el-table
      v-loading="loading"
      :data="pagedTableData"
      style="width: 100%"
      class="settings-table app-data-table"
      table-layout="fixed"
      @sort-change="onTableSortChange"
    >
      <template #empty>
        <AppTableState
          :state="tableFeedbackState"
          empty-text="暂无零件周期基准数据"
          error-action-text="重新加载"
          auth-action-text="前往登录"
          @action="onTableStateAction"
        />
      </template>

      <el-table-column prop="part_type" label="零件类型" width="160" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-white font-medium">{{ resolvePartType(row) }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="material_desc" label="零件描述" min-width="220" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.material_desc }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="machine_model" label="机床型号" width="120" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.machine_model || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="plant" label="工厂" width="108" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.plant || '通用' }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="ref_batch_qty" label="参考批量" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ row.ref_batch_qty }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="cycle_days" label="周期天数" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-brand">{{ formatPartCycleDays(row.cycle_days) }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="unit_cycle_days" label="单件周期" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ formatPartUnitCycleDays(row.unit_cycle_days) }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="sample_count" label="样本数" width="96" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ row.sample_count ?? 0 }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="cycle_source" label="周期来源" width="120" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-muted">{{ cycleSourceLabelMap[row.cycle_source || ''] || row.cycle_source || '-' }}</span>
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

    <div class="mt-6 flex justify-end">
      <el-pagination
        v-model:current-page="pageNo"
        v-model:page-size="pageSize"
        :page-sizes="pageSizes"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppStatusBadge from '../AppStatusBadge.vue'
import AppTableState from '../AppTableState.vue'
import type { TableFeedbackState } from '../../composables/useTableFeedbackState'
import type { PartCycleItem } from '../../composables/usePartCycleBaselinePage'
import type { TableSortChange } from '../../composables/useTableSort'
import type { StatusBadgeMeta } from '../../utils/statusPresentation'
import { formatPartCycleDays, formatPartUnitCycleDays } from '../../utils/partCyclePrecision'

const pageNo = defineModel<number>('pageNo', { required: true })
const pageSize = defineModel<number>('pageSize', { required: true })

defineProps<{
  sortableColumnProps: Record<string, unknown>
  loading: boolean
  pagedTableData: PartCycleItem[]
  tableFeedbackState: TableFeedbackState
  pageSizes: readonly number[]
  total: number
  cycleSourceLabelMap: Record<string, string>
  resolvePartType: (row: PartCycleItem) => string
  getActiveStatusBadgeMeta: (value?: boolean | null) => StatusBadgeMeta
  onEdit: (row: PartCycleItem) => void
  onDelete: (row: PartCycleItem) => void | Promise<void>
  onTableSortChange: (sort: TableSortChange) => void
  onTableStateAction: () => void | Promise<void>
}>()
</script>
