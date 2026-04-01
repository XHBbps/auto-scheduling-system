<template>
  <div class="tech-card p-6">
    <el-table
      v-loading="loading"
      :data="data"
      style="width: 100%"
      class="bom-list-table app-data-table"
      table-layout="fixed"
      @sort-change="$emit('sort-change', $event)"
    >
      <template #empty>
        <div class="py-10 text-text-muted">暂无数据</div>
      </template>
      <el-table-column prop="machine_material_no" label="整机物料号" width="144" show-overflow-tooltip v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-white font-medium">{{ row.machine_material_no }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="machine_material_desc" label="整机描述" min-width="200" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column prop="plant" label="工厂" width="80" align="center" v-bind="sortableColumnProps" />
      <el-table-column prop="material_no" label="上级物料号" width="140" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column prop="material_desc" label="上级物料描述" min-width="200" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column prop="bom_component_no" label="BOM组件号" width="140" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column prop="bom_component_desc" label="组件描述" min-width="200" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column prop="part_type" label="类型" width="110" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getPartTypeBadgeMeta(row.part_type, row.bom_level)" />
        </template>
      </el-table-column>
      <el-table-column prop="component_qty" label="组件数量" width="84" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num">{{ row.component_qty ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="bom_level" label="BOM层级" width="84" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num">{{ row.bom_level ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="is_top_level" label="顶层" width="80" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span :class="row.is_top_level ? 'text-brand' : 'text-text-muted'">{{ row.is_top_level ? '是' : '否' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="is_self_made" label="自制" width="80" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span :class="row.is_self_made ? 'text-brand' : 'text-text-muted'">{{ row.is_self_made ? '是' : '否' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="sync_time" label="同步时间" width="176" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-sm text-text-muted">{{ formatDateTime(row.sync_time) }}</span>
        </template>
      </el-table-column>
    </el-table>

    <div class="mt-6 flex justify-end">
      <el-pagination
        v-model:current-page="currentPageProxy"
        v-model:page-size="pageSizeProxy"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="$emit('refresh')"
        @current-change="$emit('refresh')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PropType } from 'vue'
import AppStatusBadge from '../AppStatusBadge.vue'
import type { BomItem } from '../../composables/useBomDataPage'
import type { TableSortChange } from '../../composables/useTableSort'
import { formatDateTime } from '../../utils/format'
import { getPartTypeBadgeMeta } from '../../utils/statusPresentation'

const props = defineProps({
  loading: { type: Boolean, default: false },
  data: { type: Array as PropType<BomItem[]>, default: () => [] },
  sortableColumnProps: { type: Object as PropType<Record<string, unknown>>, default: () => ({}) },
  currentPage: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  total: { type: Number, default: 0 },
})

const emit = defineEmits<{
  (event: 'update:currentPage', value: number): void
  (event: 'update:pageSize', value: number): void
  (event: 'refresh'): void
  (event: 'sort-change', value: TableSortChange): void
}>()

const currentPageProxy = computed({
  get: () => props.currentPage,
  set: (value: number) => emit('update:currentPage', value),
})

const pageSizeProxy = computed({
  get: () => props.pageSize,
  set: (value: number) => emit('update:pageSize', value),
})
</script>
