import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const pushMock = vi.fn()
const runConfirmedExportMock = vi.fn()
const feedbackState = ref<'loading' | 'ready' | 'empty' | 'error' | 'auth' | 'forbidden' | 'disabled'>('ready')

vi.mock('../utils/httpClient', () => ({
  default: {
    get: getMock,
  },
}))

vi.mock('../utils/requestCache', () => ({
  getCachedAsync: vi.fn(async (_key, _ttl, loader) => loader()),
}))

vi.mock('../utils/performance', () => ({
  measureAsync: vi.fn(async (_scope, _label, task) => task()),
}))

vi.mock('./useExportAction', () => ({
  useExportAction: () => ({
    exporting: ref(false),
    runConfirmedExport: runConfirmedExportMock,
  }),
}))

vi.mock('./useTableFeedbackState', () => ({
  useTableFeedbackState: () => ({
    tableFeedbackState: feedbackState,
    showLoadingState: vi.fn(() => {
      feedbackState.value = 'loading'
    }),
    showEmptyState: vi.fn(() => {
      feedbackState.value = 'ready'
    }),
    showErrorState: vi.fn(() => {
      feedbackState.value = 'error'
    }),
  }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  useRoute: () => ({
    fullPath: '/part-schedules',
    query: {
      contract_no: 'HT-009',
      order_no: 'SO-009',
      assembly_name: '总装',
      part_material_no: 'P-001',
      warning_level: 'abnormal',
      date_from: '2026-03-05',
      date_to: '2026-03-20',
    },
  }),
}))

const buildWrapper = async () => {
  const { usePartScheduleListPage } = await import('./usePartScheduleListPage')

  const TestComponent = defineComponent({
    setup() {
      return usePartScheduleListPage()
    },
    template: '<div />',
  })

  const wrapper = mount(TestComponent)
  await flushPromises()
  return wrapper
}

describe('usePartScheduleListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    feedbackState.value = 'ready'
    window.localStorage.clear()
    window.localStorage.setItem('part-schedule-list-visible-columns', JSON.stringify(['customer_name', 'material_no']))
    runConfirmedExportMock.mockReset()
    getMock.mockImplementation((url: string, options?: { params?: Record<string, unknown> }) => {
      if (url === '/api/part-schedules/options/assembly-names') {
        return Promise.resolve(['总装', '电控'])
      }
      if (url === '/api/part-schedules') {
        return Promise.resolve({
          total: 1,
          items: [
            {
              id: 1,
              contract_no: 'HT-009',
              order_no: 'SO-009',
              assembly_name: '总装',
              warning_level: 'abnormal',
              quantity: 3,
            },
          ],
          _params: options?.params,
        })
      }
      return Promise.resolve([])
    })
  })

  it('hydrates route query, loads cached assembly options, and fetches list data with mapped params', async () => {
    const wrapper = await buildWrapper()

    expect(wrapper.vm.searchForm.contractNo).toBe('HT-009')
    expect(wrapper.vm.searchForm.orderNo).toBe('SO-009')
    expect(wrapper.vm.searchForm.assemblyName).toBe('总装')
    expect(wrapper.vm.searchForm.partMaterialNo).toBe('P-001')
    expect(wrapper.vm.searchForm.warningLevel).toBe('abnormal')
    expect(wrapper.vm.dateRange).toEqual(['2026-03-05', '2026-03-20'])
    expect(wrapper.vm.assemblyOptions).toEqual(['总装', '电控'])
    expect(wrapper.vm.visibleColumnKeys).toEqual(['customer_name', 'material_no'])
    expect(wrapper.vm.tableData).toHaveLength(1)

    const partCall = getMock.mock.calls.find((call) => call[0] === '/api/part-schedules')
    expect(partCall?.[1]?.params).toMatchObject({
      contract_no: 'HT-009',
      order_no: 'SO-009',
      assembly_name: '总装',
      part_material_no: 'P-001',
      warning_level: 'abnormal',
      date_from: '2026-03-05',
      date_to: '2026-03-20',
    })
  })

  it('redirects to login when table feedback state is auth', async () => {
    const wrapper = await buildWrapper()
    feedbackState.value = 'auth'

    await wrapper.vm.handleTableStateAction()

    expect(pushMock).toHaveBeenCalledWith({
      name: 'AdminAuth',
      query: { redirect: '/part-schedules' },
    })
  })

  it('jumps back to machine schedule list by contract number', async () => {
    const wrapper = await buildWrapper()

    wrapper.vm.goToScheduleList({
      id: 1,
      order_line_id: 101,
      contract_no: 'HT-009',
      order_no: 'SO-009',
      assembly_name: '总装',
      production_sequence: 1,
    })

    expect(pushMock).toHaveBeenCalledWith({
      path: '/schedules',
      query: { contract_no: 'HT-009' },
    })
  })
})



  it('exports part schedule list with the current mapped filters', async () => {
    runConfirmedExportMock.mockResolvedValue(true)
    const wrapper = await buildWrapper()

    await wrapper.vm.handleExport()

    expect(runConfirmedExportMock).toHaveBeenCalledWith(
      expect.objectContaining({
        confirmTitle: '导出零件排产列表',
        fallbackFilename: expect.stringContaining('零件排产列表_'),
      }),
    )

    const exportRequest = runConfirmedExportMock.mock.calls[0][0].request
    await exportRequest()

    const exportCall = getMock.mock.calls.find((call) => call[0] === '/api/exports/part-schedules')
    expect(exportCall?.[1]?.params).toMatchObject({
      contract_no: 'HT-009',
      order_no: 'SO-009',
      assembly_name: '总装',
      part_material_no: 'P-001',
      warning_level: 'abnormal',
      date_from: '2026-03-05',
      date_to: '2026-03-20',
    })
    expect(exportCall?.[1]?.responseType).toBe('blob')
  })
