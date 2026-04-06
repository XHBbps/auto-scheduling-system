import { nextTick, ref } from 'vue'
import { describe, expect, it } from 'vitest'
import { DEFAULT_TABLE_PAGE_SIZE, TABLE_PAGE_SIZE_OPTIONS, useLocalTablePagination } from './useTablePagination'

describe('useLocalTablePagination', () => {
  const createItems = (count: number) => Array.from({ length: count }, (_, i) => i + 1)

  it('returns correct defaults', () => {
    const source = ref<number[]>([])
    const { pageNo, pageSize, pageSizes, total, pagedData } = useLocalTablePagination(() => source.value)

    expect(pageNo.value).toBe(1)
    expect(pageSize.value).toBe(DEFAULT_TABLE_PAGE_SIZE)
    expect(pageSizes).toBe(TABLE_PAGE_SIZE_OPTIONS)
    expect(total.value).toBe(0)
    expect(pagedData.value).toEqual([])
  })

  it('paginates data correctly', () => {
    const source = ref(createItems(25))
    const { pageNo, pageSize, pagedData, total } = useLocalTablePagination(() => source.value)

    expect(total.value).toBe(25)
    expect(pagedData.value).toEqual(createItems(10))

    pageNo.value = 2
    expect(pagedData.value).toEqual([11, 12, 13, 14, 15, 16, 17, 18, 19, 20])

    pageNo.value = 3
    expect(pagedData.value).toEqual([21, 22, 23, 24, 25])

    pageSize.value = 20
    // pageSize watcher resets pageNo to 1
  })

  it('resets pageNo to 1 when pageSize changes', async () => {
    const source = ref(createItems(30))
    const { pageNo, pageSize } = useLocalTablePagination(() => source.value)

    pageNo.value = 3
    pageSize.value = 20
    await nextTick()

    expect(pageNo.value).toBe(1)
  })

  it('clamps pageNo when total shrinks below current page', async () => {
    const source = ref(createItems(30))
    const { pageNo } = useLocalTablePagination(() => source.value)

    pageNo.value = 3
    source.value = createItems(15)
    await nextTick()

    expect(pageNo.value).toBe(2)
  })

  it('resetPagination sets pageNo back to 1', () => {
    const source = ref(createItems(30))
    const { pageNo, resetPagination } = useLocalTablePagination(() => source.value)

    pageNo.value = 3
    resetPagination()
    expect(pageNo.value).toBe(1)
  })
})
