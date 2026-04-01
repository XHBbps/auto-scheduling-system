<template>
  <div class="space-y-6">
    <MachineCycleBaselineSearchPanel
      v-model:search-form="searchForm"
      :rebuilding="rebuilding"
      :on-search="handleSearch"
      :on-reset="handleReset"
      :on-rebuild="handleRebuild"
      :on-add="handleAdd"
    />

    <MachineCycleBaselineTableSection
      v-model:page-no="pageNo"
      v-model:page-size="pageSize"
      :sortable-column-props="sortableColumnProps"
      :loading="loading"
      :table-data="tableData"
      :table-feedback-state="tableFeedbackState"
      :page-sizes="pageSizes"
      :total="total"
      :get-active-status-badge-meta="getActiveStatusBadgeMeta"
      :on-edit="handleEdit"
      :on-delete="handleDelete"
      :on-table-sort-change="handleTableSortChange"
      :on-table-state-action="handleTableStateAction"
      :on-fetch-data="fetchData"
    />

    <MachineCycleBaselineDialog
      v-model:visible="dialogVisible"
      v-model:form="form"
      :is-edit="isEdit"
      :submitting="submitting"
      :rules="rules"
      :on-submit="handleSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import MachineCycleBaselineDialog from '../components/machine-cycle-baseline/MachineCycleBaselineDialog.vue'
import MachineCycleBaselineSearchPanel from '../components/machine-cycle-baseline/MachineCycleBaselineSearchPanel.vue'
import MachineCycleBaselineTableSection from '../components/machine-cycle-baseline/MachineCycleBaselineTableSection.vue'
import { useMachineCycleBaselinePage } from '../composables/useMachineCycleBaselinePage'

const {
  sortableColumnProps,
  loading,
  rebuilding,
  tableData,
  tableFeedbackState,
  searchForm,
  pageNo,
  pageSize,
  pageSizes,
  total,
  dialogVisible,
  isEdit,
  submitting,
  form,
  rules,
  fetchData,
  handleAdd,
  handleEdit,
  handleDelete,
  handleRebuild,
  handleSubmit,
  handleSearch,
  handleReset,
  handleTableSortChange,
  handleTableStateAction,
  getActiveStatusBadgeMeta,
} = useMachineCycleBaselinePage()
</script>
