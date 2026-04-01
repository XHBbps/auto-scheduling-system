import { ref, type Ref } from 'vue'
import { cleanParams } from '../utils/format'
import { DEFAULT_TABLE_PAGE_SIZE, TABLE_PAGE_SIZE_OPTIONS } from './useTablePagination'
import {
  getTableSortColumnProps,
  useTableSort,
  type TableSortChange,
  type TableSortState,
} from './useTableSort'
import { useTableFeedbackState } from './useTableFeedbackState'
import { measureAsync } from '../utils/performance'

export type MaybePromise<T = void> = T | Promise<T>

export interface UseServerTableQueryOptions<TSearch extends Record<string, any>> {
  createSearchForm: () => TSearch
  initialPageSize?: number
  initialSort?: TableSortState
  searchParamKeyMap?: Partial<Record<keyof TSearch, string>>
  sortFieldMap?: Record<string, string>
  buildExtraParams?: () => Record<string, unknown>
  resetExtraState?: () => void
}

export interface UseRemoteTableQueryOptions<
  TSearch extends Record<string, any>,
  TItem,
  TResponse,
> extends UseServerTableQueryOptions<TSearch> {
  request: (params: Record<string, unknown>) => Promise<TResponse>
  resolveItems?: (response: TResponse) => TItem[]
  resolveTotal?: (response: TResponse, items: TItem[]) => number
  perfScope?: string
  perfLabel?: string
  buildPerfMeta?: (params: Record<string, unknown>) => Record<string, unknown>
}

export const useServerTableQuery = <TSearch extends Record<string, any>>(
  options: UseServerTableQueryOptions<TSearch>,
) => {
  const searchForm = ref(options.createSearchForm()) as Ref<TSearch>
  const pageNo = ref(1)
  const pageSize = ref(options.initialPageSize ?? DEFAULT_TABLE_PAGE_SIZE)
  const total = ref(0)
  const { sortField, sortOrder, buildSortParams, handleSortChange: updateSort, resetSort } = useTableSort(options.initialSort)

  const mapSearchParams = (value: TSearch) =>
    Object.entries(value).reduce<Record<string, unknown>>((acc, [key, currentValue]) => {
      const mappedKey = options.searchParamKeyMap?.[key as keyof TSearch] || key
      acc[mappedKey] = currentValue
      return acc
    }, {})

  const mapSortParams = () => {
    const params = buildSortParams()
    if (!params.sort_field) return params
    return {
      ...params,
      sort_field: options.sortFieldMap?.[params.sort_field] || params.sort_field,
    }
  }

  const buildQueryParams = (config?: { includePagination?: boolean }) => {
    const includePagination = config?.includePagination !== false
    return cleanParams({
      ...(includePagination
        ? {
            page_no: pageNo.value,
            page_size: pageSize.value,
          }
        : {}),
      ...mapSearchParams(searchForm.value),
      ...(options.buildExtraParams?.() ?? {}),
      ...mapSortParams(),
    })
  }

  const setTotal = (value?: number | null) => {
    total.value = value ?? 0
  }

  const resetSearchForm = () => {
    searchForm.value = options.createSearchForm()
    options.resetExtraState?.()
  }

  const handleSearch = (fetcher: () => MaybePromise) => {
    pageNo.value = 1
    return fetcher()
  }

  const handleReset = (fetcher: () => MaybePromise) => {
    resetSearchForm()
    resetSort()
    return handleSearch(fetcher)
  }

  const handleTableSortChange = (sort: TableSortChange, fetcher: () => MaybePromise) => {
    updateSort(sort)
    pageNo.value = 1
    return fetcher()
  }

  return {
    searchForm,
    pageNo,
    pageSize,
    pageSizes: TABLE_PAGE_SIZE_OPTIONS,
    total,
    sortField,
    sortOrder,
    buildQueryParams,
    buildSortParams: mapSortParams,
    handleSearch,
    handleReset,
    handleTableSortChange,
    resetSearchForm,
    resetSort,
    setTotal,
  }
}

const defaultResolveItems = <TItem, TResponse>(response: TResponse): TItem[] => {
  if (Array.isArray(response)) {
    return response as TItem[]
  }
  if (
    response &&
    typeof response === 'object' &&
    'items' in response &&
    Array.isArray((response as { items?: unknown }).items)
  ) {
    return ((response as { items: TItem[] }).items || []) as TItem[]
  }
  return []
}

const defaultResolveTotal = <TItem, TResponse>(response: TResponse, items: TItem[]) => {
  if (
    response &&
    typeof response === 'object' &&
    'total' in response &&
    typeof (response as { total?: unknown }).total === 'number'
  ) {
    return ((response as { total: number }).total || 0) as number
  }
  return items.length
}

export const useRemoteTableQuery = <
  TSearch extends Record<string, any>,
  TItem,
  TResponse,
>(
  options: UseRemoteTableQueryOptions<TSearch, TItem, TResponse>,
) => {
  const sortableColumnProps = getTableSortColumnProps()
  const loading = ref(false)
  const tableData = ref<TItem[]>([])
  const { tableFeedbackState, showLoadingState, showEmptyState, showErrorState } =
    useTableFeedbackState()

  const {
    searchForm,
    pageNo,
    pageSize,
    pageSizes,
    total,
    sortField,
    sortOrder,
    buildQueryParams,
    buildSortParams,
    handleSearch: triggerSearch,
    handleReset: triggerReset,
    handleTableSortChange: triggerTableSortChange,
    resetSearchForm,
    resetSort,
    setTotal,
  } = useServerTableQuery(options)

  const fetchData = async (config?: { silentLoading?: boolean }) => {
    const silentLoading = config?.silentLoading === true
    const params = buildQueryParams()
    loading.value = !silentLoading
    if (!silentLoading) {
      showLoadingState()
    }

    try {
      const response = options.perfScope
        ? await measureAsync(
            options.perfScope,
            options.perfLabel || 'fetchData',
            () => options.request(params),
            options.buildPerfMeta?.(params) || {
              silentLoading,
              pageNo: pageNo.value,
              pageSize: pageSize.value,
            },
          )
        : await options.request(params)
      const items = options.resolveItems?.(response) ?? defaultResolveItems<TItem, TResponse>(response)
      tableData.value = items
      setTotal(options.resolveTotal?.(response, items) ?? defaultResolveTotal(response, items))
      showEmptyState()
    } catch (error) {
      console.error(error)
      showErrorState(error)
      tableData.value = []
      setTotal(0)
    } finally {
      loading.value = false
    }
  }

  const handleSearch = () => triggerSearch(fetchData)
  const handleReset = () => triggerReset(fetchData)
  const handleTableSortChange = (sort: TableSortChange) => triggerTableSortChange(sort, fetchData)

  return {
    sortableColumnProps,
    tableFeedbackState,
    loading,
    tableData,
    searchForm,
    pageNo,
    pageSize,
    pageSizes,
    total,
    sortField,
    sortOrder,
    buildQueryParams,
    buildSortParams,
    fetchData,
    handleSearch,
    handleReset,
    handleTableSortChange,
    resetSearchForm,
    resetSort,
    setTotal,
  }
}
