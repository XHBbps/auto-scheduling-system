<template>
  <div class="tech-card p-6">
    <el-table
      v-loading="loading"
      :data="tableData"
      style="width: 100%"
      @sort-change="onHandleTableSortChange"
      class="app-data-table"
      table-layout="fixed"
    >
      <template #empty>
        <AppTableState
          :state="tableFeedbackState"
          :empty-text="'暂无异常记录'"
          error-action-text="重新加载"
          auth-action-text="前往登录"
          @action="onHandleTableStateAction"
        />
      </template>
      <el-table-column prop="issue_type" label="异常类型" width="132" v-bind="sortableColumnProps" />
      <el-table-column prop="issue_level" label="异常级别" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getIssueLevelBadgeMeta(row.issue_level)" />
        </template>
      </el-table-column>
      <el-table-column prop="source_system" label="来源" width="108" v-bind="sortableColumnProps" />
      <el-table-column prop="material_no" label="整机物料号" width="140">
        <template #default="{ row }">
          <span class="text-white font-medium">{{ row.material_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="custom_no" label="定制号" width="110">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.custom_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="order_no" label="销售订单" width="128">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.order_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="contract_no" label="合同号" width="128">
        <template #default="{ row }">
          <span class="text-text-secondary">{{ row.contract_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="issue_title" label="异常标题" min-width="220" show-overflow-tooltip v-bind="sortableColumnProps" />
      <el-table-column prop="status" label="状态" width="108" align="center" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <AppStatusBadge v-bind="getIssueStatusBadgeMeta(row.status)" />
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="176" v-bind="sortableColumnProps">
        <template #default="{ row }">
          <span class="font-mono-num text-sm text-text-muted">{{ formatDateTime(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="168" fixed="right" align="center">
        <template #default="{ row }">
          <template v-if="canManageIssues && row.status === 'open'">
            <el-popconfirm title="确定标记为已解决吗？" @confirm="onHandleAction(row.id, 'resolve')">
              <template #reference>
                <el-button link type="success" size="small">已解决</el-button>
              </template>
            </el-popconfirm>
            <el-popconfirm title="确定忽略此异常吗？" @confirm="onHandleAction(row.id, 'ignore')">
              <template #reference>
                <el-button link type="info" size="small">忽略</el-button>
              </template>
            </el-popconfirm>
          </template>
          <span v-else class="text-border text-sm">-</span>
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
import type { PropType } from 'vue'
import AppTableState from '../AppTableState.vue'
import AppStatusBadge from '../AppStatusBadge.vue'
import type { TableFeedbackState } from '../../composables/useTableFeedbackState'
import type { IssueItem } from '../../types/apiModels'
import { formatDateTime } from '../../utils/format'
import { getIssueLevelBadgeMeta, getIssueStatusBadgeMeta } from '../../utils/statusPresentation'

const pageNo = defineModel<number>('pageNo', { required: true })
const pageSize = defineModel<number>('pageSize', { required: true })

defineProps({
  canManageIssues: {
    type: Boolean,
    required: true,
  },
  loading: {
    type: Boolean,
    required: true,
  },
  onFetchData: {
    type: Function as PropType<() => void | Promise<void>>,
    required: true,
  },
  onHandleAction: {
    type: Function as PropType<(id: number, action: 'resolve' | 'ignore') => void | Promise<void>>,
    required: true,
  },
  onHandleTableSortChange: {
    type: Function as PropType<(sort: { prop?: string; order?: 'ascending' | 'descending' | null }) => void>,
    required: true,
  },
  onHandleTableStateAction: {
    type: Function as PropType<() => void | Promise<void>>,
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
    type: Array as PropType<IssueItem[]>,
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
})
</script>
