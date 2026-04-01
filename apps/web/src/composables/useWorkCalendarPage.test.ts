import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const pushMock = vi.fn()

vi.mock('../utils/httpClient', () => ({
  default: {
    get: getMock,
  },
}))

vi.mock('../utils/requestCache', () => ({
  getCachedAsync: vi.fn(async (_key: string, _ttl: number, loader: () => Promise<unknown>) => loader()),
}))

vi.mock('../utils/performance', () => ({
  measureAsync: vi.fn(async (_scope: string, _label: string, loader: () => Promise<unknown>) => loader()),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  useRoute: () => ({
    fullPath: '/admin/work-calendar',
  }),
}))

const createRequestError = (status: number, message: string) => {
  const error = new Error(message) as Error & { status?: number }
  error.status = status
  return error
}

const createDistribution = () => [
  {
    calendar_date: '2026-04-01',
    delivery_order_count: 1,
    delivery_quantity_sum: 2,
    trigger_order_count: 1,
    trigger_quantity_sum: 2,
    planned_start_order_count: 1,
    planned_start_quantity_sum: 2,
  },
]

const createDetail = () => ({
  summary: {
    calendar_date: '2026-04-01',
    delivery_order_count: 1,
    delivery_quantity_sum: 2,
    trigger_order_count: 1,
    trigger_quantity_sum: 2,
    planned_start_order_count: 1,
    planned_start_quantity_sum: 2,
  },
  delivery_orders: [{ order_line_id: 1 }],
  trigger_orders: [{ order_line_id: 2 }],
  planned_start_orders: [{ order_line_id: 3 }],
})

const buildWrapper = async () => {
  const { useWorkCalendarPage } = await import('./useWorkCalendarPage')
  const TestComponent = defineComponent({
    setup() {
      return useWorkCalendarPage()
    },
    template: '<div />',
  })
  const wrapper = mount(TestComponent)
  await flushPromises()
  return wrapper
}

describe('useWorkCalendarPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows auth state and redirects to login when month distribution request returns 401', async () => {
    getMock.mockRejectedValueOnce(createRequestError(401, '\u767b\u5f55\u5931\u6548'))

    const wrapper = await buildWrapper()

    expect(wrapper.vm.calendarState).toBe('auth')
    expect(wrapper.vm.showCalendarState).toBe(true)
    await wrapper.vm.handleCalendarStateAction()
    expect(pushMock).toHaveBeenCalledWith({
      name: 'AdminAuth',
      query: { redirect: '/admin/work-calendar' },
    })
  })

  it('shows forbidden state when month distribution request returns 403', async () => {
    getMock.mockRejectedValueOnce(createRequestError(403, '\u65e0\u6743\u9650'))

    const wrapper = await buildWrapper()

    expect(wrapper.vm.calendarState).toBe('forbidden')
    expect(wrapper.vm.calendarStateMessage).toContain('\u65e0\u6743\u67e5\u770b\u6392\u4ea7\u65e5\u5386')
  })

  it('retries day detail request after an error', async () => {
    getMock
      .mockResolvedValueOnce(createDistribution())
      .mockRejectedValueOnce(new Error('\u660e\u7ec6\u52a0\u8f7d\u5931\u8d25'))
      .mockResolvedValueOnce(createDetail())

    const wrapper = await buildWrapper()

    expect(wrapper.vm.calendarState).toBe('ready')

    await wrapper.vm.openDayDetail('2026-04-01')
    await flushPromises()

    expect(wrapper.vm.detailState).toBe('error')
    expect(wrapper.vm.detailStateMessage).toContain('\u660e\u7ec6\u52a0\u8f7d\u5931\u8d25')

    await wrapper.vm.handleDetailStateAction()
    await flushPromises()

    expect(getMock).toHaveBeenCalledTimes(3)
    expect(wrapper.vm.detailState).toBe('ready')
    expect(wrapper.vm.detailData.trigger_orders).toHaveLength(1)
  })
})
