import { mount } from '@vue/test-utils'
import { computed, ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const goDetailMock = vi.fn()
const calendarActionMock = vi.fn()
const detailActionMock = vi.fn()

const createComposableState = (overrides?: Record<string, unknown>) => ({
  calendarCells: computed(() => [
    {
      key: '2026-04-01',
      empty: false,
      date: '2026-04-01',
      day: 1,
      isToday: false,
      summary: {
        calendar_date: '2026-04-01',
        delivery_order_count: 1,
        delivery_quantity_sum: 2,
        trigger_order_count: 1,
        trigger_quantity_sum: 1,
        planned_start_order_count: 1,
        planned_start_quantity_sum: 1,
      },
    },
  ]),
  calendarFeedbackState: computed(() => 'empty'),
  calendarState: ref('ready'),
  calendarStateMessage: ref(''),
  changeMonth: vi.fn(),
  currentMonthStr: computed(() => '2026-04'),
  deliveryPageNo: ref(1),
  deliveryPageSize: ref(20),
  deliveryPageSizes: [20, 50, 100],
  deliveryTotal: computed(() => 1),
  detailData: ref({
    summary: {
      calendar_date: '2026-04-01',
      delivery_order_count: 1,
      delivery_quantity_sum: 2,
      trigger_order_count: 1,
      trigger_quantity_sum: 1,
      planned_start_order_count: 1,
      planned_start_quantity_sum: 1,
    },
    delivery_orders: [{ order_line_id: 1 }],
    trigger_orders: [{ order_line_id: 2 }],
    planned_start_orders: [{ order_line_id: 3 }],
  }),
  detailDialogVisible: ref(true),
  detailLoading: ref(false),
  detailFeedbackState: computed(() => 'empty'),
  detailState: ref('ready'),
  detailStateMessage: ref(''),
  detailSummary: computed(() => ({
    calendar_date: '2026-04-01',
    delivery_order_count: 1,
    delivery_quantity_sum: 2,
    trigger_order_count: 1,
    trigger_quantity_sum: 1,
    planned_start_order_count: 1,
    planned_start_quantity_sum: 1,
  })),
  formatQuantity: (value?: string | number | null) => (value == null ? '-' : String(value)),
  goToCurrentMonth: vi.fn(),
  goToScheduleDetail: goDetailMock,
  handleCalendarStateAction: calendarActionMock,
  handleDeliverySortChange: vi.fn(),
  handlePlannedStartSortChange: vi.fn(),
  handleDetailStateAction: detailActionMock,
  handleTriggerSortChange: vi.fn(),
  labels: {
    title: '????',
    subtitle: '????',
    delivery: '??',
    trigger: '????',
    plannedStart: '??',
    today: '??',
    backToCurrentMonth: '????',
    monthDelivery: '??',
    monthTrigger: '????',
    monthPlannedStart: '??',
    orderUnit: '??',
    quantityUnit: '??',
    deliveryShort: '??',
    triggerShort: '??',
    plannedStartShort: '??',
    orderShort: '?',
    quantityShort: '?',
    detailTitleSuffix: '????',
    deliveryOrderTab: '????',
    triggerOrderTab: '????',
    plannedStartOrderTab: '?????',
    emptyDeliveryOrders: '????????',
    emptyTriggerOrders: '????????',
    emptyPlannedStartOrders: '?????????',
    contractNo: '???',
    orderNo: '????',
    productModel: '????',
    materialNo: '???',
    quantity: '??',
    scheduleStatus: '????',
    plannedStartDate: '?????',
    confirmedDeliveryDate: '?????',
    triggerDate: '????',
    actions: '??',
    detailAction: '??',
  },
  loading: ref(false),
  monthSummary: computed(() => ({
    deliveryOrderCount: 1,
    deliveryQuantitySum: 2,
    triggerOrderCount: 1,
    triggerQuantitySum: 1,
    plannedStartOrderCount: 1,
    plannedStartQuantitySum: 1,
  })),
  openDayDetail: vi.fn(),
  pagedDeliveryOrders: computed(() => [{ order_line_id: 1 }]),
  pagedPlannedStartOrders: computed(() => [{ order_line_id: 3 }]),
  pagedTriggerOrders: computed(() => [{ order_line_id: 2 }]),
  plannedStartPageNo: ref(1),
  plannedStartPageSize: ref(20),
  plannedStartPageSizes: [20, 50, 100],
  plannedStartTotal: computed(() => 1),
  selectedDate: ref('2026-04-01'),
  showCalendarState: computed(() => false),
  showDetailState: computed(() => false),
  triggerPageNo: ref(1),
  triggerPageSize: ref(20),
  triggerPageSizes: [20, 50, 100],
  triggerTotal: computed(() => 1),
  weekdayLabels: ['??', '??', '??', '??', '??', '??', '??'],
  ...overrides,
})

let composableState = createComposableState()

vi.mock('../composables/useWorkCalendarPage', () => ({
  useWorkCalendarPage: () => composableState,
}))

const ElButtonStub = {
  emits: ['click'],
  template: "<button @click=\"$emit('click')\"><slot /></button>",
}

const ElDialogStub = {
  props: ['modelValue', 'title'],
  template: '<div><div>{{ title }}</div><slot /></div>',
}

const ElTabsStub = {
  props: ['modelValue'],
  template: '<div><slot /></div>',
}

const ElTabPaneStub = {
  props: ['label', 'name'],
  template: '<section><div>{{ label }}</div><slot /></section>',
}

const ElTableStub = {
  template: '<div><slot /><slot name="empty" /></div>',
}

const ElTableColumnStub = {
  template: '<div />',
}

describe('WorkCalendarPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    composableState = createComposableState()
  })

  it('renders delivery and planned-start summary cards plus placeholder metrics', async () => {
    const component = (await import('./WorkCalendarPage.vue')).default
    const wrapper = mount(component, {
      global: {
        directives: {
          loading: () => undefined,
        },
        stubs: {
          'el-button': ElButtonStub,
          'el-dialog': ElDialogStub,
          'el-tabs': ElTabsStub,
          'el-tab-pane': ElTabPaneStub,
          'el-table': ElTableStub,
          'el-table-column': ElTableColumnStub,
          'el-pagination': true,
        },
      },
    })

    expect(wrapper.findAll('.summary-card')).toHaveLength(2)
    expect(wrapper.findAll('.summary-metric--placeholder')).toHaveLength(2)
    expect(wrapper.text()).toContain('???')
    expect(wrapper.text()).toContain('???')
    expect(wrapper.text()).toContain('???')
    expect(wrapper.text()).toContain('???')
    expect(wrapper.text()).toContain('--')
  })

  it('renders calendar auth state and triggers the action handler', async () => {
    composableState = createComposableState({
      calendarFeedbackState: computed(() => 'auth'),
      calendarState: ref('auth'),
      calendarStateMessage: ref('??????????????????????'),
      showCalendarState: computed(() => true),
      detailDialogVisible: ref(false),
    })

    const component = (await import('./WorkCalendarPage.vue')).default
    const wrapper = mount(component, {
      global: {
        directives: {
          loading: () => undefined,
        },
        stubs: {
          'el-button': ElButtonStub,
          'el-dialog': ElDialogStub,
          'el-tabs': ElTabsStub,
          'el-tab-pane': ElTabPaneStub,
          'el-table': ElTableStub,
          'el-table-column': ElTableColumnStub,
          'el-pagination': true,
        },
      },
    })

    expect(wrapper.text()).toContain('??????????????????????')
    expect(wrapper.text()).toContain('????')
    await wrapper.find('.app-table-state__action').trigger('click')
    expect(calendarActionMock).toHaveBeenCalled()
  })
})
