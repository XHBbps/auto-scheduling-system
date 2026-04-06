import { describe, expect, it, vi } from 'vitest'
import { useRemoteTableQuery } from './useServerTableQuery'

const { measureAsyncMock } = vi.hoisted(() => ({
  measureAsyncMock: vi.fn(async (_scope, _label, task) => task()),
}))

vi.mock('../utils/performance', () => ({
  measureAsync: measureAsyncMock,
}))

describe('useRemoteTableQuery', () => {
  it('records performance metrics when perf scope is configured', async () => {
    measureAsyncMock.mockClear()
    const request = vi.fn().mockResolvedValue({
      total: 1,
      items: [{ id: 1 }],
    })

    const { fetchData } = useRemoteTableQuery({
      createSearchForm: () => ({
        keyword: '',
      }),
      request,
      perfScope: 'issueManagement',
      perfLabel: 'fetchIssueTable',
      buildPerfMeta: (params) => ({
        hasKeyword: Boolean(params.keyword),
      }),
    })

    await fetchData()

    expect(measureAsyncMock).toHaveBeenCalledWith(
      'issueManagement',
      'fetchIssueTable',
      expect.any(Function),
      expect.objectContaining({
        hasKeyword: false,
      }),
    )
  })

  it('hydrates remote table data and total on success', async () => {
    const request = vi.fn().mockResolvedValue({
      total: 2,
      items: [
        { id: 1, name: 'A' },
        { id: 2, name: 'B' },
      ],
    })

    const {
      loading,
      tableData,
      total,
      tableFeedbackState,
      searchForm,
      fetchData,
      handleSearch,
      handleReset,
    } = useRemoteTableQuery({
      createSearchForm: () => ({
        keyword: '',
      }),
      request,
    })

    searchForm.value.keyword = 'soul'
    await fetchData()

    expect(request).toHaveBeenCalledWith(
      {
        keyword: 'soul',
        page_no: 1,
        page_size: 10,
      },
      expect.any(AbortSignal),
    )
    expect(tableData.value).toEqual([
      { id: 1, name: 'A' },
      { id: 2, name: 'B' },
    ])
    expect(total.value).toBe(2)
    expect(tableFeedbackState.value).toBe('empty')
    expect(loading.value).toBe(false)

    searchForm.value.keyword = 'next'
    await handleSearch()
    expect(request).toHaveBeenLastCalledWith(
      {
        keyword: 'next',
        page_no: 1,
        page_size: 10,
      },
      expect.any(AbortSignal),
    )

    await handleReset()
    expect(searchForm.value.keyword).toBe('')
  })

  it('maps failed remote requests to table feedback state', async () => {
    const request = vi.fn().mockRejectedValue(Object.assign(new Error('forbidden'), { status: 403 }))

    const { tableData, total, tableFeedbackState, fetchData } = useRemoteTableQuery({
      createSearchForm: () => ({
        keyword: '',
      }),
      request,
    })

    await fetchData()

    expect(tableData.value).toEqual([])
    expect(total.value).toBe(0)
    expect(tableFeedbackState.value).toBe('forbidden')
  })

  it('maps internal search and sort field names to api parameter names', async () => {
    const request = vi.fn().mockResolvedValue({
      total: 1,
      items: [{ id: 1 }],
    })

    const { searchForm, handleTableSortChange, fetchData } = useRemoteTableQuery({
      createSearchForm: () => ({
        sourceSystem: '',
      }),
      searchParamKeyMap: {
        sourceSystem: 'source_system',
      },
      sortFieldMap: {
        createdAt: 'created_at',
      },
      request,
    })

    searchForm.value.sourceSystem = 'sap'
    handleTableSortChange({ prop: 'createdAt', order: 'descending' })
    await fetchData()

    expect(request).toHaveBeenLastCalledWith(
      {
        page_no: 1,
        page_size: 10,
        source_system: 'sap',
        sort_field: 'created_at',
        sort_order: 'desc',
      },
      expect.any(AbortSignal),
    )
  })
})
