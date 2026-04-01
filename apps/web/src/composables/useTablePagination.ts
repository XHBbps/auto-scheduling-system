import { computed, ref, watch } from 'vue'

export const DEFAULT_TABLE_PAGE_SIZE = 10
export const TABLE_PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const

export const useLocalTablePagination = <T>(source: () => T[]) => {
  const pageNo = ref(1)
  const pageSize = ref(DEFAULT_TABLE_PAGE_SIZE)

  const total = computed(() => source().length)

  const pagedData = computed(() => {
    const start = (pageNo.value - 1) * pageSize.value
    return source().slice(start, start + pageSize.value)
  })

  const resetPagination = () => {
    pageNo.value = 1
  }

  watch(pageSize, () => {
    pageNo.value = 1
  })

  watch(total, (value) => {
    const maxPage = Math.max(1, Math.ceil(value / pageSize.value))
    if (pageNo.value > maxPage) {
      pageNo.value = maxPage
    }
  })

  return {
    pageNo,
    pageSize,
    pageSizes: TABLE_PAGE_SIZE_OPTIONS,
    total,
    pagedData,
    resetPagination,
  }
}
