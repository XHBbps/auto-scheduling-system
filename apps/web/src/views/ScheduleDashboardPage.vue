<template>
  <div class="space-y-6">
    <DashboardHeader
      v-model:dashboard-mode="dashboardMode"
      :current-mode-description="currentModeDescription"
      :loading="isDashboardOverviewLoading"
      :mode-options="modeOptions"
      :today-label="todayLabel"
      @reload="reloadDashboardOverview"
    />

    <DashboardStateCard
      v-if="!isDashboardOverviewReady"
      :body-text="dashboardStateBodyText"
      :loading="isDashboardOverviewLoading"
      :show-login-action="showDashboardLoginAction"
      :show-retry-action="showDashboardRetryAction"
      :title="dashboardStateTitle"
      @go-login="handleGoToLogin"
      @reload="reloadDashboardOverview"
    />

    <template v-else>
      <DashboardKpiGrid :cards="cards" />

      <DashboardChartsSection
        :panels="chartPanels"
        :set-chart-ref="setChartRef"
        :trigger-panel-action="triggerPanelAction"
      />

      <DashboardActiveTable
        v-model:page-no="activeTablePageNo"
        v-model:page-size="activeTablePageSize"
        :description="activeTableDescription"
        :empty-text="activeTableEmptyText"
        :format-quantity="formatQuantity"
        :page-sizes="activeTablePageSizes"
        :rows="pagedActiveTableRows"
        :sortable-column-props="sortableColumnProps"
        :title="activeTableTitle"
        :total="activeTableTotal"
        @row-click="goToDetail"
        @sort-change="handleTableSortChange"
        @view-all="handleViewAllActiveTable"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import DashboardActiveTable from '../components/dashboard/DashboardActiveTable.vue'
import DashboardChartsSection from '../components/dashboard/DashboardChartsSection.vue'
import DashboardHeader from '../components/dashboard/DashboardHeader.vue'
import DashboardKpiGrid from '../components/dashboard/DashboardKpiGrid.vue'
import DashboardStateCard from '../components/dashboard/DashboardStateCard.vue'
import { useScheduleDashboardPage } from '../composables/useScheduleDashboardPage'

const {
  activeTableDescription,
  activeTableEmptyText,
  activeTablePageNo,
  activeTablePageSize,
  activeTablePageSizes,
  activeTableTitle,
  activeTableTotal,
  cards,
  chartPanels,
  currentModeDescription,
  dashboardMode,
  dashboardStateBodyText,
  dashboardStateTitle,
  formatQuantity,
  goToDetail,
  handleGoToLogin,
  handleTableSortChange,
  handleViewAllActiveTable,
  isDashboardOverviewLoading,
  isDashboardOverviewReady,
  modeOptions,
  pagedActiveTableRows,
  reloadDashboardOverview,
  setChartRef,
  showDashboardLoginAction,
  showDashboardRetryAction,
  sortableColumnProps,
  todayLabel,
  triggerPanelAction,
} = useScheduleDashboardPage()
</script>
