<template>
  <div class="space-y-6">
    <WorkCalendarHeader
      :labels="labels"
      :current-month-str="currentMonthStr"
      @change-month="changeMonth"
      @go-current-month="goToCurrentMonth"
    />

    <AppTableState
      v-if="showCalendarState"
      class="tech-card"
      :state="calendarFeedbackState"
      :text="calendarStateMessage"
      :error-action-text="'\u91cd\u65b0\u52a0\u8f7d'"
      :auth-action-text="'\u524d\u5f80\u767b\u5f55'"
      @action="handleCalendarStateAction"
    />

    <template v-else>
      <WorkCalendarSummaryCards
        :labels="labels"
        :month-summary="monthSummary"
        :format-quantity="formatQuantity"
      />

      <WorkCalendarGrid
        :calendar-cells="calendarCells"
        :labels="labels"
        :loading="loading"
        :weekday-labels="weekdayLabels"
        :format-quantity="formatQuantity"
        @open-day-detail="openDayDetail"
      />
    </template>

    <WorkCalendarDetailDialog
      v-model="detailDialogVisible"
      :delivery-page-no="deliveryPageNo"
      :delivery-page-size="deliveryPageSize"
      :delivery-page-sizes="deliveryPageSizes"
      :delivery-total="deliveryTotal"
      :detail-data="detailData"
      :detail-loading="detailLoading"
      :detail-state="detailFeedbackState"
      :detail-state-message="detailStateMessage"
      :detail-summary="detailSummary"
      :format-quantity="formatQuantity"
      :labels="labels"
      :paged-delivery-orders="pagedDeliveryOrders"
      :paged-planned-start-orders="pagedPlannedStartOrders"
      :paged-trigger-orders="pagedTriggerOrders"
      :planned-start-page-no="plannedStartPageNo"
      :planned-start-page-size="plannedStartPageSize"
      :planned-start-page-sizes="plannedStartPageSizes"
      :planned-start-total="plannedStartTotal"
      :selected-date="selectedDate"
      :show-detail-state="showDetailState"
      :sortable-column-props="sortableColumnProps"
      :trigger-page-no="triggerPageNo"
      :trigger-page-size="triggerPageSize"
      :trigger-page-sizes="triggerPageSizes"
      :trigger-total="triggerTotal"
      @update:delivery-page-no="deliveryPageNo = $event"
      @update:delivery-page-size="deliveryPageSize = $event"
      @update:planned-start-page-no="plannedStartPageNo = $event"
      @update:planned-start-page-size="plannedStartPageSize = $event"
      @update:trigger-page-no="triggerPageNo = $event"
      @update:trigger-page-size="triggerPageSize = $event"
      @delivery-sort-change="handleDeliverySortChange"
      @planned-start-sort-change="handlePlannedStartSortChange"
      @trigger-sort-change="handleTriggerSortChange"
      @go-detail="goToScheduleDetail"
      @state-action="handleDetailStateAction"
    />
  </div>
</template>

<script setup lang="ts">
import AppTableState from '../components/AppTableState.vue'
import WorkCalendarDetailDialog from '../components/work-calendar/WorkCalendarDetailDialog.vue'
import WorkCalendarGrid from '../components/work-calendar/WorkCalendarGrid.vue'
import WorkCalendarHeader from '../components/work-calendar/WorkCalendarHeader.vue'
import WorkCalendarSummaryCards from '../components/work-calendar/WorkCalendarSummaryCards.vue'
import { getTableSortColumnProps } from '../composables/useTableSort'
import { useWorkCalendarPage } from '../composables/useWorkCalendarPage'

const sortableColumnProps = getTableSortColumnProps()
const {
  calendarCells,
  calendarFeedbackState,
  calendarStateMessage,
  changeMonth,
  currentMonthStr,
  deliveryPageNo,
  deliveryPageSize,
  deliveryPageSizes,
  deliveryTotal,
  detailData,
  detailDialogVisible,
  detailLoading,
  detailFeedbackState,
  detailStateMessage,
  detailSummary,
  formatQuantity,
  goToCurrentMonth,
  goToScheduleDetail,
  handleCalendarStateAction,
  handleDeliverySortChange,
  handlePlannedStartSortChange,
  handleDetailStateAction,
  handleTriggerSortChange,
  labels,
  loading,
  monthSummary,
  openDayDetail,
  pagedDeliveryOrders,
  pagedPlannedStartOrders,
  pagedTriggerOrders,
  plannedStartPageNo,
  plannedStartPageSize,
  plannedStartPageSizes,
  plannedStartTotal,
  selectedDate,
  showCalendarState,
  showDetailState,
  triggerPageNo,
  triggerPageSize,
  triggerPageSizes,
  triggerTotal,
  weekdayLabels,
} = useWorkCalendarPage()
</script>
