import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const pushMock = vi.fn()
const chartInstanceFactory = () => ({
  dispose: vi.fn(),
  resize: vi.fn(),
})
const renderDonutChartMock = vi.fn(() => chartInstanceFactory())
const renderVerticalBarChartMock = vi.fn(() => chartInstanceFactory())
const renderHorizontalBarChartMock = vi.fn(() => chartInstanceFactory())
const renderLineChartMock = vi.fn(() => chartInstanceFactory())

vi.mock('../utils/httpClient', () => ({
  default: {
    get: getMock,
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  useRoute: () => ({
    fullPath: '/dashboard',
  }),
}))

vi.mock('../utils/dashboardChartOptions', () => ({
  renderDonutChart: renderDonutChartMock,
  renderVerticalBarChart: renderVerticalBarChartMock,
  renderHorizontalBarChart: renderHorizontalBarChartMock,
  renderLineChart: renderLineChartMock,
}))

const createOverview = (overrides?: Partial<Record<string, unknown>>) => ({
  machine_summary: {
    total_orders: 12,
    scheduled_orders: 8,
    unscheduled_orders: 4,
    abnormal_orders: 2,
    status_counts: [
      { key: 'scheduled', count: 8 },
      { key: 'schedulable', count: 4 },
    ],
    planned_end_month_counts: [{ key: '2026-03', count: 12 }],
    warning_orders: [
      {
        order_line_id: 101,
        contract_no: 'HT-001',
        order_no: 'SO-001',
        customer_name: '扬力',
        business_group: '冲压事业群',
        product_model: 'YL-160',
        material_no: 'M-001',
        quantity: 2,
        confirmed_delivery_date: '2026-03-28',
        planned_end_date: '2026-03-27',
        schedule_status: 'scheduled_stale',
        warning_level: 'abnormal',
      },
    ],
  },
  part_summary: {
    total_parts: 24,
    abnormal_parts: 3,
    warning_counts: [{ key: 'abnormal', count: 3 }],
    top_assemblies: [{ assembly_name: '总装', count: 10 }],
  },
  today_summary: {
    delivery_count: 2,
    unscheduled_count: 1,
    abnormal_count: 1,
  },
  week_summary: {
    delivery_count: 6,
    unscheduled_count: 2,
    abnormal_count: 1,
  },
  month_summary: {
    delivery_count: 12,
    unscheduled_count: 4,
    abnormal_count: 2,
  },
  delivery_trends: {
    day: [
      { key: '2026-03-26', label: '03-26', scheduled_count: 1, delivery_count: 2 },
      { key: '2026-03-27', label: '03-27', scheduled_count: 3, delivery_count: 1 },
    ],
    week: [
      { key: '2026-03-24', label: '03-24', scheduled_count: 6, delivery_count: 5 },
      { key: '2026-03-31', label: '03-31', scheduled_count: 4, delivery_count: 3 },
    ],
    month: [
      { key: '2026-03', label: '2026-03', scheduled_count: 12, delivery_count: 10 },
      { key: '2026-04', label: '2026-04', scheduled_count: 9, delivery_count: 11 },
    ],
  },
  business_group_summary: [
    { business_group: '冲压事业群', order_count: 7, total_amount: '720000' },
    { business_group: '自动化事业群', order_count: 5, total_amount: '500000' },
  ],
  abnormal_machine_orders: [
    {
      order_line_id: 101,
      contract_no: 'HT-001',
      order_no: 'SO-001',
      customer_name: '扬力',
      business_group: '冲压事业群',
      product_model: 'YL-160',
      material_no: 'M-001',
      quantity: 2,
      confirmed_delivery_date: '2026-03-28',
      planned_end_date: '2026-03-27',
      schedule_status: 'scheduled_stale',
      warning_level: 'abnormal',
    },
  ],
  delivery_risk_orders: [
    {
      order_line_id: 102,
      contract_no: 'HT-002',
      order_no: 'SO-002',
      customer_name: '扬力',
      business_group: '自动化事业群',
      product_model: 'YL-200',
      material_no: 'M-002',
      quantity: 1,
      confirmed_delivery_date: '2026-03-30',
      planned_end_date: '2026-03-29',
      schedule_status: 'scheduled_stale',
      warning_level: 'abnormal',
    },
  ],
  ...overrides,
})

const createEmptyOverview = () =>
  createOverview({
    machine_summary: {
      total_orders: 0,
      scheduled_orders: 0,
      unscheduled_orders: 0,
      abnormal_orders: 0,
      status_counts: [],
      planned_end_month_counts: [],
      warning_orders: [],
    },
    part_summary: {
      total_parts: 0,
      abnormal_parts: 0,
      warning_counts: [],
      top_assemblies: [],
    },
    today_summary: {
      delivery_count: 0,
      unscheduled_count: 0,
      abnormal_count: 0,
    },
    week_summary: {
      delivery_count: 0,
      unscheduled_count: 0,
      abnormal_count: 0,
    },
    month_summary: {
      delivery_count: 0,
      unscheduled_count: 0,
      abnormal_count: 0,
    },
    delivery_trends: {
      day: [],
      week: [],
      month: [],
    },
    business_group_summary: [],
    abnormal_machine_orders: [],
    delivery_risk_orders: [],
  })

const createRequestError = (status: number, message: string) => {
  const error = new Error(message) as Error & { status?: number }
  error.status = status
  return error
}

const ElButtonStub = defineComponent({
  emits: ['click'],
  template: '<button @click="$emit(\'click\')"><slot /></button>',
})

const ElTableStub = defineComponent({
  template: '<div><slot /><slot name="empty" /></div>',
})

const ElTableColumnStub = defineComponent({
  template: '<div />',
})

const buildWrapper = async () => {
  vi.resetModules()
  const component = (await import('./ScheduleDashboardPage.vue')).default

  const wrapper = mount(component, {
    global: {
      directives: {
        loading: () => undefined,
      },
      stubs: {
        transition: false,
        'el-icon': true,
        'el-button': ElButtonStub,
        'el-table': ElTableStub,
        'el-table-column': ElTableColumnStub,
        'el-pagination': true,
      },
    },
  })
  await flushPromises()
  return { wrapper }
}

describe('ScheduleDashboardPage', () => {
  beforeEach(() => {
    window.localStorage.clear()
    getMock.mockReset()
    pushMock.mockReset()
    renderDonutChartMock.mockClear()
    renderVerticalBarChartMock.mockClear()
    renderHorizontalBarChartMock.mockClear()
    renderLineChartMock.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders planner dashboard content from overview endpoint only', async () => {
    getMock.mockResolvedValue(createOverview())

    const { wrapper } = await buildWrapper()

    expect(getMock).toHaveBeenCalledWith('/api/dashboard/overview', { silentError: true })
    expect(wrapper.find('[data-test="dashboard-content"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="dashboard-state-card"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('今日交付')
    expect(wrapper.text()).toContain('30天交付风险')
    expect(wrapper.text()).toContain('重点关注订单')
    expect(wrapper.text()).toContain('排产交付趋势')
    expect(wrapper.text()).toContain('未来 30 天交付风险订单')
    expect(wrapper.text()).not.toContain('更多信息')
    expect(renderLineChartMock).toHaveBeenCalled()
    expect(renderDonutChartMock).toHaveBeenCalled()
  })

  it('forces a new overview request when refresh is clicked after a successful load', async () => {
    getMock.mockResolvedValue(createOverview())

    const { wrapper } = await buildWrapper()

    expect(getMock).toHaveBeenCalledTimes(1)

    const refreshButton = wrapper.findAll('button').find((item) => item.text().includes('刷新总览'))
    expect(refreshButton).toBeTruthy()

    await refreshButton!.trigger('click')
    await flushPromises()

    expect(getMock).toHaveBeenCalledTimes(2)
  })

  it('switches to management view and renders business-group chart and abnormal pool', async () => {
    getMock.mockResolvedValue(createOverview())

    const { wrapper } = await buildWrapper()

    const managementButton = wrapper.findAll('button').find((item) => item.text().includes('管理'))
    expect(managementButton).toBeTruthy()

    await managementButton!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('整机排产总量')
    expect(wrapper.text()).toContain('计划完工节奏')
    expect(wrapper.text()).toContain('整机状态分布')
    expect(wrapper.text()).toContain('事业群订单数据')
    expect(wrapper.text()).toContain('异常整机订单池')
    expect(renderVerticalBarChartMock).toHaveBeenCalled()
  })

  it('updates planner trend dimension when week view is selected', async () => {
    getMock.mockResolvedValue(createOverview())

    const { wrapper } = await buildWrapper()
    const initialCalls = renderLineChartMock.mock.calls.length

    const weekButton = wrapper.findAll('button').find((item) => item.text() === '周')
    expect(weekButton).toBeTruthy()

    await weekButton!.trigger('click')
    await flushPromises()

    expect(renderLineChartMock.mock.calls.length).toBeGreaterThan(initialCalls)
  })

  it('shows empty state when overview endpoint returns no summary data', async () => {
    getMock.mockResolvedValue(createEmptyOverview())

    const { wrapper } = await buildWrapper()

    expect(wrapper.find('[data-test="dashboard-content"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="dashboard-state-title"]').text()).toContain('暂无总览数据')
    expect(wrapper.find('[data-test="dashboard-state-message"]').text()).toContain('整机或零件统计数据')
  })

  it('shows auth state when overview request is rejected with 401/403', async () => {
    getMock.mockRejectedValue(createRequestError(401, '登录已过期'))

    const { wrapper } = await buildWrapper()

    expect(wrapper.find('[data-test="dashboard-state-title"]').text()).toContain('登录状态已失效')
    expect(wrapper.find('[data-test="dashboard-state-message"]').text()).toContain('重新登录')
    expect(wrapper.text()).toContain('前往登录')
  })

  it('shows error state and supports retry after a normal request failure', async () => {
    getMock
      .mockRejectedValueOnce(createRequestError(500, '总览接口异常'))
      .mockResolvedValueOnce(createOverview())

    const { wrapper } = await buildWrapper()

    expect(wrapper.find('[data-test="dashboard-state-title"]').text()).toContain('总览加载失败')
    expect(wrapper.find('[data-test="dashboard-state-message"]').text()).toContain('总览接口异常')

    const retryButton = wrapper.findAll('button').find((item) => item.text().includes('重新加载'))
    expect(retryButton).toBeTruthy()

    await retryButton!.trigger('click')
    await flushPromises()

    expect(getMock).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[data-test="dashboard-content"]').exists()).toBe(true)
  })
})
