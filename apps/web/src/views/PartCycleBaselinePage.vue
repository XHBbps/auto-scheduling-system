<template>
  <div class="space-y-6">
    <PartCycleBaselineSearchPanel
      v-model:search-form="searchForm"
      :rebuild-loading="rebuildLoading"
      :on-search="handleSearch"
      :on-reset="handleReset"
      :on-rebuild="handleRebuild"
      :on-add="handleAdd"
    />

    <PartCycleBaselineTableSection
      v-model:page-no="pageNo"
      v-model:page-size="pageSize"
      :sortable-column-props="sortableColumnProps"
      :loading="loading"
      :paged-table-data="pagedTableData"
      :table-feedback-state="tableFeedbackState"
      :page-sizes="pageSizes"
      :total="total"
      :cycle-source-label-map="cycleSourceLabelMap"
      :resolve-part-type="resolvePartType"
      :get-active-status-badge-meta="getActiveStatusBadgeMeta"
      :on-edit="handleEdit"
      :on-delete="handleDelete"
      :on-table-sort-change="handleTableSortChange"
      :on-table-state-action="handleTableStateAction"
    />

    <PartCycleBaselineDialog
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
import PartCycleBaselineDialog from '../components/part-cycle-baseline/PartCycleBaselineDialog.vue'
import PartCycleBaselineSearchPanel from '../components/part-cycle-baseline/PartCycleBaselineSearchPanel.vue'
import PartCycleBaselineTableSection from '../components/part-cycle-baseline/PartCycleBaselineTableSection.vue'
import { usePartCycleBaselinePage } from '../composables/usePartCycleBaselinePage'

const {
  sortableColumnProps,
  loading,
  rebuildLoading,
  pagedTableData,
  tableFeedbackState,
  searchForm,
  pageNo,
  pageSize,
  pageSizes,
  total,
  cycleSourceLabelMap,
  dialogVisible,
  isEdit,
  submitting,
  form,
  rules,
  resolvePartType,
  handleAdd,
  handleEdit,
  handleDelete,
  handleSubmit,
  handleRebuild,
  handleSearch,
  handleReset,
  handleTableSortChange,
  handleTableStateAction,
  getActiveStatusBadgeMeta,
} = usePartCycleBaselinePage()
</script>
