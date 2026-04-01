<template>
  <div class="space-y-6">
    <AssemblyTimeSearchPanel
      v-model:search-form="searchForm"
      :handle-search="handleSearch"
      :handle-reset="handleReset"
      :handle-add="handleAdd"
    />

    <AssemblyTimeTableSection
      v-model:current-page="pageNo"
      v-model:page-size="pageSize"
      :loading="loading"
      :data="pagedTableData"
      :page-sizes="pageSizes"
      :total="total"
      :sortable-column-props="sortableColumnProps"
      :handle-edit="handleEdit"
      :handle-delete="handleDelete"
      :handle-sort-change="handleTableSortChange"
    />

    <AssemblyTimeDialog
      v-model:visible="dialogVisible"
      v-model:form="form"
      :rules="rules"
      :is-edit="isEdit"
      :submitting="submitting"
      @submit="handleSubmit"
      @production-sequence-change="handleProductionSequenceChange"
    />
  </div>
</template>

<script setup lang="ts">
import AssemblyTimeDialog from '../components/assembly-time-config/AssemblyTimeDialog.vue'
import AssemblyTimeSearchPanel from '../components/assembly-time-config/AssemblyTimeSearchPanel.vue'
import AssemblyTimeTableSection from '../components/assembly-time-config/AssemblyTimeTableSection.vue'
import { useAssemblyTimeConfigPage } from '../composables/useAssemblyTimeConfigPage'
import { getTableSortColumnProps } from '../composables/useTableSort'

const sortableColumnProps = getTableSortColumnProps()
const {
  searchForm,
  loading,
  pagedTableData,
  pageNo,
  pageSize,
  pageSizes,
  total,
  dialogVisible,
  isEdit,
  submitting,
  form,
  rules,
  handleAdd,
  handleEdit,
  handleDelete,
  handleSubmit,
  handleSearch,
  handleReset,
  handleTableSortChange,
  handleProductionSequenceChange,
} = useAssemblyTimeConfigPage()
</script>
