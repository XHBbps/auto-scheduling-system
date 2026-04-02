import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const postMock = vi.fn()
const successMessageMock = vi.fn()
const warningMessageMock = vi.fn()
const errorMessageMock = vi.fn()
const confirmMock = vi.fn()

vi.mock('../utils/httpClient', () => ({
  default: {
    get: getMock,
    post: postMock,
  },
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: successMessageMock,
      warning: warningMessageMock,
      error: errorMessageMock,
      info: vi.fn(),
    },
    ElMessageBox: {
      confirm: confirmMock,
    },
  }
})

const buildWrapper = async () => {
  const { useSyncConsolePage } = await import('./useSyncConsolePage')
  const TestComponent = defineComponent({
    setup() {
      return useSyncConsolePage()
    },
    template: '<div />',
  })
  const wrapper = mount(TestComponent)
  await flushPromises()
  return wrapper
}

describe('useSyncConsolePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getMock.mockImplementation((url: string) => {
      if (url === '/api/admin/sync/schedule') {
        return Promise.resolve({
          enabled: false,
          state: 'paused',
          timezone: 'Asia/Shanghai',
          jobs: [],
        })
      }
      if (url === '/api/admin/sync/observability') {
        return Promise.resolve({
          snapshot_total: 0,
          missing_bom_snapshot_count: 0,
          open_missing_bom_issue_count: 0,
          distinct_machine_bom_count: 0,
          running_job_count: 0,
          bom_backfill_queue: {
            pending: 0,
            processing: 0,
            retry_wait: 0,
            success: 0,
            failed: 0,
            paused: 0,
            retry_wait_due: 0,
            failure_kind_counts: {},
            oldest_pending_age_minutes: null,
            latest_failed_items: [],
          },
          latest_sales_plan_job: null,
          latest_research_job: null,
          latest_auto_bom_job: null,
        })
      }
      if (url === '/api/admin/sync-logs') {
        return Promise.resolve({
          total: 0,
          page_no: 1,
          page_size: 50,
          items: [],
        })
      }
      if (url.startsWith('/api/admin/sync-logs/')) {
        return Promise.resolve({
          id: 1,
          job_type: 'sales_plan',
          source_system: 'guandata',
          status: 'completed',
          success_count: 1,
          fail_count: 0,
          message: '同步完成',
        })
      }
      return Promise.resolve({})
    })
    confirmMock.mockResolvedValue('confirm')
  })

  it(
    'returns proper button labels and descriptions for sync states',
    async () => {
      const wrapper = await buildWrapper()

      expect(wrapper.vm.syncButtonLabel('salesPlan')).toBe('手动同步')
      expect(wrapper.vm.getSyncStateDescription('salesPlan')).toBe('')

      wrapper.vm.syncState.salesPlan.status = 'queued'
      expect(wrapper.vm.syncButtonLabel('salesPlan')).toBe('已排队...')
      expect(wrapper.vm.getSyncStateDescription('salesPlan')).toContain('等待 worker 认领执行')

      wrapper.vm.syncState.salesPlan.status = 'running'
      expect(wrapper.vm.syncButtonLabel('salesPlan')).toBe('执行中...')

      wrapper.vm.syncState.salesPlan.status = 'noop'
      wrapper.vm.syncState.salesPlan.message = '当前无需执行'
      expect(wrapper.vm.getSyncStateDescription('salesPlan')).toBe('当前无需执行')
    },
    10000,
  )

  it('warns and blocks bom sync when material and plant are missing', async () => {
    const wrapper = await buildWrapper()
    const bomSource = wrapper.vm.syncSources.find((item: { key: string }) => item.key === 'bom')
    expect(bomSource).toBeTruthy()

    await wrapper.vm.handleSync(bomSource!)

    // Validation fires before confirm dialog — confirm should NOT be called
    expect(confirmMock).not.toHaveBeenCalled()
    expect(postMock).not.toHaveBeenCalled()
    expect(warningMessageMock).toHaveBeenCalledWith('请输入物料号和工厂后再执行 BOM 同步')
  })

  it('marks sync as noop when backend says no execution is needed', async () => {
    postMock.mockResolvedValue({
      status: 'noop',
      message: '当前没有需要执行的同步任务',
      job_id: null,
    })
    const wrapper = await buildWrapper()
    const salesPlanSource = wrapper.vm.syncSources.find((item: { key: string }) => item.key === 'salesPlan')
    expect(salesPlanSource).toBeTruthy()

    await wrapper.vm.handleSync(salesPlanSource!)

    expect(wrapper.vm.syncState.salesPlan.status).toBe('noop')
    expect(warningMessageMock).toHaveBeenCalledWith('当前没有需要执行的同步任务')
  })

  it('retries bom backfill queue item and refreshes observability', async () => {
    getMock.mockImplementation((url: string) => {
      if (url === '/api/admin/sync/schedule') {
        return Promise.resolve({
          enabled: false,
          state: 'paused',
          timezone: 'Asia/Shanghai',
          jobs: [],
        })
      }
      if (url === '/api/admin/sync/observability') {
        return Promise.resolve({
          snapshot_total: 0,
          missing_bom_snapshot_count: 0,
          open_missing_bom_issue_count: 0,
          distinct_machine_bom_count: 0,
          running_job_count: 0,
          bom_backfill_queue: {
            pending: 0,
            processing: 0,
            retry_wait: 1,
            success: 0,
            failed: 0,
            paused: 0,
            retry_wait_due: 1,
            failure_kind_counts: { transient_error: 1 },
            oldest_pending_age_minutes: null,
            latest_failed_items: [
              {
                id: 99,
                material_no: 'MAT-001',
                plant: '1000',
                source: 'sales_plan',
                status: 'retry_wait',
                priority: 10,
                fail_count: 2,
                next_retry_at: '2026-03-26 18:00:00',
              },
            ],
          },
          latest_sales_plan_job: null,
          latest_research_job: null,
          latest_auto_bom_job: null,
        })
      }
      if (url === '/api/admin/sync-logs') {
        return Promise.resolve({
          total: 0,
          page_no: 1,
          page_size: 50,
          items: [],
        })
      }
      return Promise.resolve({})
    })
    postMock.mockResolvedValue({
      updated_count: 1,
      message: '已重置 1 条 BOM 补数队列记录。',
    })

    const wrapper = await buildWrapper()
    const item = wrapper.vm.syncObservability.bom_backfill_queue.latest_failed_items[0]

    expect(wrapper.vm.canRetryBomBackfillItem(item)).toBe(true)
    expect(wrapper.vm.getQueueRetryHint(item)).toContain('自动重试')

    await wrapper.vm.handleRetryBomBackfillItem(item)

    expect(confirmMock).toHaveBeenCalledTimes(1)
    expect(postMock).toHaveBeenCalledWith('/api/admin/sync/bom-backfill-queue/retry', {
      ids: [99],
    })
    expect(successMessageMock).toHaveBeenCalledWith('已重置 1 条 BOM 补数队列记录。')
  })
})
