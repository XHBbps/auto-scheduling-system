<template>
  <el-dialog
    :model-value="modelValue"
    :title="selectedDate ? `${selectedDate} ${labels.detailTitleSuffix}` : labels.detailTitleSuffix"
    width="1180px"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div v-loading="detailLoading" class="space-y-6">
      <AppTableState
        v-if="showDetailState"
        class="tech-card"
        :state="detailState"
        :text="detailStateMessage"
        :error-action-text="'重新加载'"
        :auth-action-text="'前往登录'"
        @action="$emit('state-action')"
      />

      <template v-else>
        <div class="detail-summary-grid">
          <div class="detail-summary-card detail-summary-card--delivery">
            <span class="detail-summary-card__label">{{ '应交付' }}</span>
            <span class="detail-summary-card__value font-mono-num">{{ detailSummary.delivery_order_count }}</span>
            <span class="detail-summary-card__hint">
              {{ labels.orderUnit }} {{ detailSummary.delivery_order_count }} / {{ labels.quantityUnit }}
              {{ formatQuantity(detailSummary.delivery_quantity_sum) }}
            </span>
          </div>
          <div class="detail-summary-card detail-summary-card--trigger">
            <span class="detail-summary-card__label">{{ '应触发' }}</span>
            <span class="detail-summary-card__value font-mono-num">{{ detailSummary.trigger_order_count }}</span>
            <span class="detail-summary-card__hint">
              {{ labels.orderUnit }} {{ detailSummary.trigger_order_count }} / {{ labels.quantityUnit }}
              {{ formatQuantity(detailSummary.trigger_quantity_sum) }}
            </span>
          </div>
          <div class="detail-summary-card detail-summary-card--planned-start">
            <span class="detail-summary-card__label">{{ '应开工' }}</span>
            <span class="detail-summary-card__value font-mono-num">{{ detailSummary.planned_start_order_count }}</span>
            <span class="detail-summary-card__hint">
              {{ labels.orderUnit }} {{ detailSummary.planned_start_order_count }} / {{ labels.quantityUnit }}
              {{ formatQuantity(detailSummary.planned_start_quantity_sum) }}
            </span>
          </div>
        </div>

        <el-tabs v-model="activeDetailTab">
          <el-tab-pane :label="`${labels.deliveryOrderTab} (${detailData.delivery_orders.length})`" name="delivery">
            <el-table
              :data="pagedDeliveryOrders"
              class="app-data-table"
              table-layout="fixed"
              @sort-change="$emit('delivery-sort-change', $event)"
            >
              <template #empty>
                <div class="py-8 text-text-muted">{{ labels.emptyDeliveryOrders }}</div>
              </template>
              <el-table-column prop="contract_no" :label="labels.contractNo" width="140" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="order_no" :label="labels.orderNo" width="140" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="product_model" :label="labels.productModel" width="160" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="material_no" :label="labels.materialNo" width="160" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="quantity" :label="labels.quantity" width="100" align="center" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <span class="font-mono-num">{{ formatQuantity(row.quantity) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="schedule_status" :label="labels.scheduleStatus" width="120" align="center" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <AppStatusBadge v-bind="getScheduleStatusBadgeMeta(row.schedule_status)" />
                </template>
              </el-table-column>
              <el-table-column prop="planned_start_date" :label="labels.plannedStartDate" width="120" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <span class="font-mono-num text-text-secondary">{{ formatDate(row.planned_start_date) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="confirmed_delivery_date" :label="labels.confirmedDeliveryDate" width="120" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <span class="font-mono-num text-text-secondary">{{ formatDate(row.confirmed_delivery_date) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="labels.actions" width="96" fixed="right" align="center">
                <template #default="{ row }">
                  <el-button link class="!text-brand" @click="$emit('go-detail', row.order_line_id)">{{ labels.detailAction }}</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="mt-6 flex justify-end">
              <el-pagination
                :current-page="deliveryPageNo"
                :page-size="deliveryPageSize"
                :page-sizes="deliveryPageSizes"
                :total="deliveryTotal"
                layout="total, sizes, prev, pager, next, jumper"
                @update:current-page="$emit('update:deliveryPageNo', $event)"
                @update:page-size="$emit('update:deliveryPageSize', $event)"
              />
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`${labels.triggerOrderTab} (${detailData.trigger_orders.length})`" name="trigger">
            <el-table
              :data="pagedTriggerOrders"
              class="app-data-table"
              table-layout="fixed"
              @sort-change="$emit('trigger-sort-change', $event)"
            >
              <template #empty>
                <div class="py-8 text-text-muted">{{ labels.emptyTriggerOrders }}</div>
              </template>
              <el-table-column prop="contract_no" :label="labels.contractNo" width="140" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="order_no" :label="labels.orderNo" width="140" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="product_model" :label="labels.productModel" width="160" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="material_no" :label="labels.materialNo" width="160" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="quantity" :label="labels.quantity" width="100" align="center" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <span class="font-mono-num">{{ formatQuantity(row.quantity) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="schedule_status" :label="labels.scheduleStatus" width="120" align="center" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <AppStatusBadge v-bind="getScheduleStatusBadgeMeta(row.schedule_status)" />
                </template>
              </el-table-column>
              <el-table-column prop="trigger_date" :label="labels.triggerDate" width="120" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <span class="font-mono-num text-text-secondary">{{ formatDate(row.trigger_date) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="confirmed_delivery_date" :label="labels.confirmedDeliveryDate" width="120" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <span class="font-mono-num text-text-secondary">{{ formatDate(row.confirmed_delivery_date) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="labels.actions" width="96" fixed="right" align="center">
                <template #default="{ row }">
                  <el-button link class="!text-brand" @click="$emit('go-detail', row.order_line_id)">{{ labels.detailAction }}</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="mt-6 flex justify-end">
              <el-pagination
                :current-page="triggerPageNo"
                :page-size="triggerPageSize"
                :page-sizes="triggerPageSizes"
                :total="triggerTotal"
                layout="total, sizes, prev, pager, next, jumper"
                @update:current-page="$emit('update:triggerPageNo', $event)"
                @update:page-size="$emit('update:triggerPageSize', $event)"
              />
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`${labels.plannedStartOrderTab} (${detailData.planned_start_orders.length})`" name="planned_start">
            <el-table
              :data="pagedPlannedStartOrders"
              class="app-data-table"
              table-layout="fixed"
              @sort-change="$emit('planned-start-sort-change', $event)"
            >
              <template #empty>
                <div class="py-8 text-text-muted">{{ labels.emptyPlannedStartOrders }}</div>
              </template>
              <el-table-column prop="contract_no" :label="labels.contractNo" width="140" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="order_no" :label="labels.orderNo" width="140" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="product_model" :label="labels.productModel" width="160" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="material_no" :label="labels.materialNo" width="160" show-overflow-tooltip v-bind="sortableColumnProps" />
              <el-table-column prop="quantity" :label="labels.quantity" width="100" align="center" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <span class="font-mono-num">{{ formatQuantity(row.quantity) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="schedule_status" :label="labels.scheduleStatus" width="120" align="center" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <AppStatusBadge v-bind="getScheduleStatusBadgeMeta(row.schedule_status)" />
                </template>
              </el-table-column>
              <el-table-column prop="planned_start_date" :label="labels.plannedStartDate" width="120" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <span class="font-mono-num text-text-secondary">{{ formatDate(row.planned_start_date) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="confirmed_delivery_date" :label="labels.confirmedDeliveryDate" width="120" v-bind="sortableColumnProps">
                <template #default="{ row }">
                  <span class="font-mono-num text-text-secondary">{{ formatDate(row.confirmed_delivery_date) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="labels.actions" width="96" fixed="right" align="center">
                <template #default="{ row }">
                  <el-button link class="!text-brand" @click="$emit('go-detail', row.order_line_id)">{{ labels.detailAction }}</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="mt-6 flex justify-end">
              <el-pagination
                :current-page="plannedStartPageNo"
                :page-size="plannedStartPageSize"
                :page-sizes="plannedStartPageSizes"
                :total="plannedStartTotal"
                layout="total, sizes, prev, pager, next, jumper"
                @update:current-page="$emit('update:plannedStartPageNo', $event)"
                @update:page-size="$emit('update:plannedStartPageSize', $event)"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { PropType } from 'vue'
import AppTableState from '../AppTableState.vue'
import AppStatusBadge from '../AppStatusBadge.vue'
import { formatDate } from '../../utils/format'
import { getScheduleStatusBadgeMeta } from '../../utils/statusPresentation'
import type { ScheduleCalendarDayDetailResponse, ScheduleCalendarDaySummary, ScheduleCalendarOrderItem } from '../../types/apiModels'
import type { WorkCalendarLabels } from '../../composables/useWorkCalendarPage'
import type { TableFeedbackState } from '../../composables/useTableFeedbackState'

const props = defineProps({
  deliveryPageNo: {
    type: Number,
    required: true,
  },
  deliveryPageSize: {
    type: Number,
    required: true,
  },
  deliveryPageSizes: {
    type: Array as PropType<readonly number[]>,
    required: true,
  },
  deliveryTotal: {
    type: Number,
    required: true,
  },
  detailData: {
    type: Object as PropType<ScheduleCalendarDayDetailResponse>,
    required: true,
  },
  detailLoading: {
    type: Boolean,
    required: true,
  },
  detailState: {
    type: String as PropType<TableFeedbackState>,
    required: true,
  },
  detailStateMessage: {
    type: String,
    required: true,
  },
  detailSummary: {
    type: Object as PropType<ScheduleCalendarDaySummary>,
    required: true,
  },
  formatQuantity: {
    type: Function as PropType<(value?: string | number | null) => string>,
    required: true,
  },
  labels: {
    type: Object as PropType<WorkCalendarLabels>,
    required: true,
  },
  modelValue: {
    type: Boolean,
    required: true,
  },
  pagedDeliveryOrders: {
    type: Array as PropType<ScheduleCalendarOrderItem[]>,
    required: true,
  },
  pagedPlannedStartOrders: {
    type: Array as PropType<ScheduleCalendarOrderItem[]>,
    required: true,
  },
  pagedTriggerOrders: {
    type: Array as PropType<ScheduleCalendarOrderItem[]>,
    required: true,
  },
  plannedStartPageNo: {
    type: Number,
    required: true,
  },
  plannedStartPageSize: {
    type: Number,
    required: true,
  },
  plannedStartPageSizes: {
    type: Array as PropType<readonly number[]>,
    required: true,
  },
  plannedStartTotal: {
    type: Number,
    required: true,
  },
  selectedDate: {
    type: String,
    required: true,
  },
  showDetailState: {
    type: Boolean,
    required: true,
  },
  sortableColumnProps: {
    type: Object as PropType<Record<string, unknown>>,
    required: true,
  },
  triggerPageNo: {
    type: Number,
    required: true,
  },
  triggerPageSize: {
    type: Number,
    required: true,
  },
  triggerPageSizes: {
    type: Array as PropType<readonly number[]>,
    required: true,
  },
  triggerTotal: {
    type: Number,
    required: true,
  },
})

defineEmits<{
  (e: 'delivery-sort-change', sort: { prop?: string; order?: 'ascending' | 'descending' | null }): void
  (e: 'go-detail', orderLineId: number): void
  (e: 'planned-start-sort-change', sort: { prop?: string; order?: 'ascending' | 'descending' | null }): void
  (e: 'state-action'): void
  (e: 'trigger-sort-change', sort: { prop?: string; order?: 'ascending' | 'descending' | null }): void
  (e: 'update:deliveryPageNo', value: number): void
  (e: 'update:deliveryPageSize', value: number): void
  (e: 'update:modelValue', value: boolean): void
  (e: 'update:plannedStartPageNo', value: number): void
  (e: 'update:plannedStartPageSize', value: number): void
  (e: 'update:triggerPageNo', value: number): void
  (e: 'update:triggerPageSize', value: number): void
}>()

const activeDetailTab = ref<'delivery' | 'trigger' | 'planned_start'>('delivery')

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      activeDetailTab.value = 'delivery'
    }
  },
)

watch(
  () => props.selectedDate,
  () => {
    activeDetailTab.value = 'delivery'
  },
)
</script>

<style scoped>
.detail-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.detail-summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 96px;
  border-radius: 16px;
  border: 1px solid transparent;
  padding: 14px;
}

.detail-summary-card--delivery {
  border-color: rgba(56, 189, 248, 0.18);
  background: rgba(56, 189, 248, 0.1);
  color: #7dd3fc;
}

.detail-summary-card--trigger {
  border-color: rgba(250, 204, 21, 0.18);
  background: rgba(250, 204, 21, 0.1);
  color: #fde68a;
}

.detail-summary-card--planned-start {
  border-color: rgba(74, 222, 128, 0.18);
  background: rgba(74, 222, 128, 0.1);
  color: #86efac;
}

.detail-summary-card__label {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
}

.detail-summary-card__value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
}

.detail-summary-card__hint {
  margin-top: auto;
  color: rgba(232, 234, 236, 0.88);
  line-height: 1.45;
  font-size: 12px;
}

:deep(.el-dialog) {
  border-radius: 24px;
  background: #121413;
}

:deep(.el-dialog__title) {
  color: #ffffff;
}

:deep(.el-dialog__body) {
  padding-top: 12px;
}

:deep(.el-tabs__item) {
  color: #a0aab2;
}

:deep(.el-tabs__item.is-active) {
  color: #82d695;
}

:deep(.el-tabs__active-bar) {
  background-color: #82d695;
}

@media (max-width: 960px) {
  .detail-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .detail-summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
