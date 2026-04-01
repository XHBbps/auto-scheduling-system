<template>
  <div class="space-y-6">
    <MachineScheduleSearchForm
      v-model:date-range="dateRange"
      :exporting="exporting"
      :product-series-options="productSeriesOptions"
      v-model:search-form="searchForm"
      @export="handleExport"
      @reset="handleReset"
      @search="handleSearch"
    />

    <MachineScheduleTableSection
      v-model:page-no="pageNo"
      v-model:page-size="pageSize"
      v-model:visible-column-keys="visibleColumnKeys"
      :format-amount="formatAmount"
      :format-machine-quantity="formatMachineQuantity"
      :get-run-action-state="getRunActionState"
      :loading="loading"
      :optional-columns="optionalColumns"
      :page-sizes="pageSizes"
      :part-schedule-loading="partScheduleLoading"
      :sortable-column-props="sortableColumnProps"
      :table-data="tableData"
      :table-feedback-state="tableFeedbackState"
      :total="total"
      @fetch-data="fetchData"
      @go-detail="goToDetail"
      @reset-visible-columns="resetVisibleColumns"
      @run-part-schedule="handleRunPartSchedule"
      @table-sort-change="handleTableSortChange"
      @table-state-action="handleTableStateAction"
    />
  </div>
</template>

<script setup lang="ts">
import MachineScheduleSearchForm from '../components/machine-schedule/MachineScheduleSearchForm.vue'
import MachineScheduleTableSection from '../components/machine-schedule/MachineScheduleTableSection.vue'
import { useMachineScheduleListPage } from '../composables/useMachineScheduleListPage'

const {
  dateRange,
  exporting,
  fetchData,
  formatAmount,
  formatMachineQuantity,
  getRunActionState,
  goToDetail,
  handleExport,
  handleReset,
  handleRunPartSchedule,
  handleSearch,
  handleTableSortChange,
  handleTableStateAction,
  loading,
  optionalColumns,
  pageNo,
  pageSize,
  pageSizes,
  partScheduleLoading,
  productSeriesOptions,
  resetVisibleColumns,
  searchForm,
  sortableColumnProps,
  tableData,
  tableFeedbackState,
  total,
  visibleColumnKeys,
} = useMachineScheduleListPage()
</script>

