<template>
  <div class="tech-card p-6">
    <el-table
      v-loading="loading"
      :data="data"
      row-key="node_key"
      table-layout="fixed"
      lazy
      :load="loadTreeNode"
      :tree-props="{ children: 'children', hasChildren: 'has_children' }"
      class="bom-tree-table app-data-table"
      style="width: 100%"
      @sort-change="handleSortChange"
    >
      <template #empty>
        <div class="py-10 text-text-muted">
          {{ machineMaterialNo ? '未找到对应 BOM 树' : '暂无 BOM 树数据' }}
        </div>
      </template>

      <el-table-column prop="material_no" label="当前节点料号" min-width="192" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <template v-if="row.is_load_more">
            <el-button
              link
              type="primary"
              class="load-more-btn"
              :loading="row.loading_more"
              @click.stop="handleLoadMore(row)"
            >
              加载更多（{{ row.loaded_children || 0 }}/{{ row.total_children || 0 }}）
            </el-button>
          </template>
          <span
            v-else
            class="table-ellipsis font-mono-num text-white/90"
            :title="row.material_no || '-'"
          >
            {{ row.material_no || '-' }}
          </span>
        </template>
      </el-table-column>

      <el-table-column prop="machine_material_no" label="整机物料号" min-width="156" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span
            v-if="!row.is_load_more"
            class="table-ellipsis font-mono-num text-white/90"
            :title="row.machine_material_no || '-'"
          >
            {{ row.machine_material_no || '-' }}
          </span>
        </template>
      </el-table-column>

      <el-table-column prop="material_desc" label="当前节点描述" min-width="220" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span
            v-if="!row.is_load_more"
            class="table-ellipsis text-text-secondary"
            :title="row.material_desc || '-'"
          >
            {{ row.material_desc || '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="parent_material_no" label="上级物料号" min-width="140" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span
            v-if="!row.is_load_more"
            class="table-ellipsis font-mono-num text-text-secondary"
            :title="row.parent_material_no || '-'"
          >
            {{ row.parent_material_no || '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="part_type" label="类型" width="110" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge
            v-if="!row.is_load_more"
            v-bind="getPartTypeBadgeMeta(row.part_type, row.bom_level)"
          />
        </template>
      </el-table-column>
      <el-table-column prop="component_qty" label="数量" width="84" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span v-if="!row.is_load_more" class="font-mono-num">{{ row.component_qty ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="bom_level" label="层级" width="76" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span v-if="!row.is_load_more" class="font-mono-num">{{ row.bom_level ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="is_self_made" label="自制" width="88" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span v-if="!row.is_load_more" :class="row.is_self_made ? 'text-brand' : 'text-text-muted'">{{ row.is_self_made ? '是' : '否' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="sync_time" label="同步时间" width="176" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span v-if="!row.is_load_more" class="font-mono-num text-sm text-text-muted">{{ formatDateTime(row.sync_time) }}</span>
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
import type { BomTreeNode } from '../../composables/useBomDataPage'
import type { TableSortChange } from '../../composables/useTableSort'
import { formatDateTime } from '../../utils/format'
import { getPartTypeBadgeMeta } from '../../utils/statusPresentation'

const props = defineProps({
  loading: { type: Boolean, default: false },
  data: { type: Array as PropType<BomTreeNode[]>, default: () => [] },
  machineMaterialNo: { type: String, default: '' },
  sortableColumnProps: { type: Object as PropType<Record<string, unknown>>, default: () => ({}) },
  currentPage: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  pageSizes: { type: Array as PropType<readonly number[]>, default: () => [] },
  total: { type: Number, default: 0 },
  loadTreeNode: {
    type: Function as PropType<(row: BomTreeNode, treeNode: unknown, resolve: (data: BomTreeNode[]) => void) => void>,
    required: true,
  },
  handleLoadMore: { type: Function as PropType<(row: BomTreeNode) => void>, required: true },
  handleSortChange: { type: Function as PropType<(sort: TableSortChange) => void>, required: true },
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

<style scoped>
:deep(.bom-tree-table .el-table__body td) {
  vertical-align: middle;
}

:deep(.bom-tree-table .el-table__body-wrapper) {
  contain: layout paint style;
}

:deep(.bom-tree-table .el-table__body .el-table__row td:first-child .el-table__expand-icon),
:deep(.bom-tree-table .el-table__body .el-table__row td:first-child .el-table__indent),
:deep(.bom-tree-table .el-table__body .el-table__row td:first-child .el-table__placeholder) {
  align-self: center;
  margin-top: 0;
}

:deep(.bom-tree-table .el-table__body .el-table__row td:first-child .el-table__expand-icon) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.table-ellipsis {
  display: inline-block;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.load-more-btn {
  padding: 0 !important;
  font-size: 13px;
  font-weight: 500;
}
</style>
