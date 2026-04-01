<template>
  <div class="space-y-6">
    <PartScheduleSearchForm
      v-model:date-range="dateRange"
      v-model:search-form="searchForm"
      :assembly-options="assemblyOptions"
      :exporting="exporting"
      @reset="handleReset"
      @search="handleSearch"
      @export="handleExport"
    />

    <PartScheduleTableSection
      v-model:page-no="pageNo"
      v-model:page-size="pageSize"
      v-model:visible-column-keys="visibleColumnKeys"
      :format-amount="formatAmount"
      :format-assembly-days="formatAssemblyDays"
      :format-cycle-days="formatCycleDays"
      :format-quantity="formatQuantity"
      :loading="loading"
      :optional-columns="optionalColumns"
      :page-sizes="pageSizes"
      :sortable-column-props="sortableColumnProps"
      :table-data="tableData"
      :table-feedback-state="tableFeedbackState"
      :total="total"
      @fetch-data="fetchData"
      @go-to-schedule-list="goToScheduleList"
      @reset-visible-columns="resetVisibleColumns"
      @table-sort-change="handleTableSortChange"
      @table-state-action="handleTableStateAction"
    />
  </div>
</template>

<script setup lang="ts">
import PartScheduleSearchForm from '../components/part-schedule/PartScheduleSearchForm.vue'
import PartScheduleTableSection from '../components/part-schedule/PartScheduleTableSection.vue'
import { usePartScheduleListPage } from '../composables/usePartScheduleListPage'

const {
  assemblyOptions,
  dateRange,
  exporting,
  fetchData,
  formatAmount,
  formatAssemblyDays,
  formatCycleDays,
  formatQuantity,
  goToScheduleList,
  handleExport,
  handleReset,
  handleSearch,
  handleTableSortChange,
  handleTableStateAction,
  loading,
  optionalColumns,
  pageNo,
  pageSize,
  pageSizes,
  resetVisibleColumns,
  searchForm,
  sortableColumnProps,
  tableData,
  tableFeedbackState,
  total,
  visibleColumnKeys,
} = usePartScheduleListPage()
</script>

