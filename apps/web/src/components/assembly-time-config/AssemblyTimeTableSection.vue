<template>
  <div class="tech-card p-6">
    <el-table
      v-loading="loading"
      :data="data"
      style="width: 100%"
      class="settings-table app-data-table"
      table-layout="fixed"
      @sort-change="handleSortChange"
    >
      <template #empty>
        <div class="py-10 text-text-muted">暂无装配时长数据</div>
      </template>
      <el-table-column prop="machine_model" label="机床型号" width="144" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-white font-medium">{{ row.machine_model }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="product_series" label="产品系列" width="120" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.product_series }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="assembly_name" label="装配名称" width="180" v-bind="sortableColumnProps" />
      <el-table-column prop="assembly_time_days" label="装配天数" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-brand">{{ parseFloat(row.assembly_time_days) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="is_final_assembly" label="是否总装" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span v-if="row.is_final_assembly" class="text-brand">&#x2705;</span>
          <span v-else class="text-border">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="production_sequence" label="生产顺序" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-text-secondary">{{ row.production_sequence }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="is_default" label="是否默认值" width="120" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getDefaultValueBadgeMeta(row.is_default)" />
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
            <el-button link class="!text-brand hover:!text-brand/80" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="mt-6 flex justify-end">
      <el-pagination
        v-model:current-page="currentPageProxy"
        v-model:page-size="pageSizeProxy"
        :page-sizes="pageSizes"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PropType } from 'vue'
import AppStatusBadge from '../AppStatusBadge.vue'
import type { AssemblyTimeItem } from '../../types/apiModels'
import type { TableSortChange } from '../../composables/useTableSort'
import { getDefaultValueBadgeMeta } from '../../utils/statusPresentation'

const props = defineProps({
  loading: { type: Boolean, default: false },
  data: { type: Array as PropType<AssemblyTimeItem[]>, default: () => [] },
  sortableColumnProps: { type: Object as PropType<Record<string, unknown>>, default: () => ({}) },
  currentPage: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  pageSizes: { type: Array as PropType<readonly number[]>, default: () => [] },
  total: { type: Number, default: 0 },
  handleEdit: {
    type: Function as PropType<(row: AssemblyTimeItem) => void>,
    required: true,
  },
  handleDelete: {
    type: Function as PropType<(row: AssemblyTimeItem) => void>,
    required: true,
  },
  handleSortChange: {
    type: Function as PropType<(sort: TableSortChange) => void>,
    required: true,
  },
})

const emit = defineEmits<{
  (event: 'update:currentPage', value: number): void
  (event: 'update:pageSize', value: number): void
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
