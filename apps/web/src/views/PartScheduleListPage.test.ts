import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const fetchDataMock = vi.fn()
const handleSearchMock = vi.fn()

vi.mock('../composables/usePartScheduleListPage', () => ({
  usePartScheduleListPage: () => ({
    assemblyOptions: [],
    dateRange: [],
    fetchData: fetchDataMock,
    formatAmount: vi.fn(),
    formatAssemblyDays: vi.fn(),
    formatCycleDays: vi.fn(),
    formatQuantity: vi.fn(),
    goToScheduleList: vi.fn(),
    handleReset: vi.fn(),
    handleSearch: handleSearchMock,
    handleTableSortChange: vi.fn(),
    handleTableStateAction: vi.fn(),
    loading: false,
    optionalColumns: [],
    pageNo: 1,
    pageSize: 10,
    pageSizes: [10, 20, 50, 100],
    resetVisibleColumns: vi.fn(),
    searchForm: {},
    sortableColumnProps: {},
    tableData: [],
    tableFeedbackState: 'ready',
    total: 0,
    visibleColumnKeys: [],
  }),
}))

describe('PartScheduleListPage', () => {
  it('uses fetchData for pagination events instead of resetting search state', async () => {
    const component = (await import('./PartScheduleListPage.vue')).default
    const wrapper = mount(component, {
      global: {
        stubs: {
          PartScheduleSearchForm: true,
          PartScheduleTableSection: {
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
