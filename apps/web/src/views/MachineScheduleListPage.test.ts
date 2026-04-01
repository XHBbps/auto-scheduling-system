import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const fetchDataMock = vi.fn()
const handleSearchMock = vi.fn()

vi.mock('../composables/useMachineScheduleListPage', () => ({
  useMachineScheduleListPage: () => ({
    dateRange: [],
    exporting: false,
    fetchData: fetchDataMock,
    formatAmount: vi.fn(),
    formatMachineQuantity: vi.fn(),
    getRunActionState: vi.fn(() => ({ disabled: false, reason: '' })),
    goToDetail: vi.fn(),
    handleExport: vi.fn(),
    handleReset: vi.fn(),
    handleRunPartSchedule: vi.fn(),
    handleSearch: handleSearchMock,
    handleTableSortChange: vi.fn(),
    handleTableStateAction: vi.fn(),
    loading: false,
    optionalColumns: [],
    pageNo: 1,
    pageSize: 10,
    pageSizes: [10, 20, 50, 100],
    partScheduleLoading: {},
    productSeriesOptions: [],
    resetVisibleColumns: vi.fn(),
    searchForm: {},
    sortableColumnProps: {},
    tableData: [],
    tableFeedbackState: 'ready',
    total: 0,
    visibleColumnKeys: [],
  }),
}))

describe('MachineScheduleListPage', () => {
  it('uses fetchData for pagination events instead of resetting search state', async () => {
    const component = (await import('./MachineScheduleListPage.vue')).default
    const wrapper = mount(component, {
      global: {
        stubs: {
          MachineScheduleSearchForm: true,
          MachineScheduleTableSection: {
            template: '<button @click="$emit(\'fetch-data\')">page</button>',
          },
        },
      },
    })

    await wrapper.get('button').trigger('click')

    expect(fetchDataMock).toHaveBeenCalledTimes(1)
    expect(handleSearchMock).not.toHaveBeenCalled()
  })
})
