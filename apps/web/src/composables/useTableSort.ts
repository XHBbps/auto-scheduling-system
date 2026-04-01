import { ref } from 'vue'

export type ApiSortOrder = 'asc' | 'desc' | undefined
export type ElementSortOrder = 'ascending' | 'descending' | null
export const DEFAULT_TABLE_SORT_ORDERS: ElementSortOrder[] = ['ascending', 'descending', null]

export interface TableSortState {
  sortField?: string
  sortOrder?: ApiSortOrder
}

export interface TableSortChange {
  prop?: string
  order?: ElementSortOrder
}

export interface LocalSortConfig<T> {
  getValue?: Partial<Record<string, (row: T) => unknown>>
  compare?: Partial<Record<string, (left: unknown, right: unknown, leftRow: T, rightRow: T) => number>>
  isStickyBottom?: (row: T) => boolean
}

const collator = new Intl.Collator('zh-CN', {
  numeric: true,
  sensitivity: 'base',
})

const normalizeElementSortOrder = (order?: ElementSortOrder): ApiSortOrder => {
  if (order === 'ascending') return 'asc'
  if (order === 'descending') return 'desc'
  return undefined
}

const isDateLikeString = (value: string) =>
  /^\d{4}-\d{2}-\d{2}/.test(value) || /^\d{4}\/\d{2}\/\d{2}/.test(value)

const toComparableValue = (value: unknown): string | number | null => {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return Number.isNaN(value) ? null : value
  if (typeof value === 'boolean') return value ? 1 : 0
  if (value instanceof Date) return value.getTime()
  if (typeof value === 'string') {
    if (isDateLikeString(value)) {
      const timestamp = Date.parse(value)
      if (!Number.isNaN(timestamp)) return timestamp
    }
    return value
  }
  return String(value)
}

const defaultCompare = <T>(left: unknown, right: unknown, _leftRow: T, _rightRow: T) => {
  const normalizedLeft = toComparableValue(left)
  const normalizedRight = toComparableValue(right)

  if (normalizedLeft === null && normalizedRight === null) return 0
  if (normalizedLeft === null) return 1
  if (normalizedRight === null) return -1

  if (typeof normalizedLeft === 'number' && typeof normalizedRight === 'number') {
    return normalizedLeft - normalizedRight
  }

  return collator.compare(String(normalizedLeft), String(normalizedRight))
}

export const applyLocalSort = <T extends Record<string, any>>(
  data: T[],
  state: TableSortState,
  config: LocalSortConfig<T> = {},
) => {
  if (!state.sortField || !state.sortOrder) {
    return [...data]
  }

  const { sortField, sortOrder } = state
  const isStickyBottom = config.isStickyBottom || (() => false)
  const valueGetter = config.getValue?.[sortField] || ((row: T) => row[sortField])
  const comparator = config.compare?.[sortField] || defaultCompare<T>
  const direction = sortOrder === 'desc' ? -1 : 1

  return [...data].sort((leftRow, rightRow) => {
    const leftSticky = isStickyBottom(leftRow)
    const rightSticky = isStickyBottom(rightRow)
    if (leftSticky && rightSticky) return 0
    if (leftSticky) return 1
    if (rightSticky) return -1

    const result = comparator(
      valueGetter(leftRow),
      valueGetter(rightRow),
      leftRow,
      rightRow,
    )
    return result * direction
  })
}

export const getTableSortColumnProps = () => ({
  sortable: 'custom' as const,
  'sort-orders': DEFAULT_TABLE_SORT_ORDERS,
})

export const useTableSort = (initialState?: TableSortState) => {
  const sortField = ref(initialState?.sortField)
  const sortOrder = ref<ApiSortOrder>(initialState?.sortOrder)

  const handleSortChange = ({ prop, order }: TableSortChange) => {
    sortField.value = prop || undefined
    sortOrder.value = normalizeElementSortOrder(order)
  }

  const buildSortParams = () => {
    if (!sortField.value || !sortOrder.value) {
      return {}
    }
    return {
      sort_field: sortField.value,
      sort_order: sortOrder.value,
    }
  }

  const resetSort = () => {
    sortField.value = undefined
    sortOrder.value = undefined
  }

  return {
    sortField,
    sortOrder,
    handleSortChange,
    buildSortParams,
    resetSort,
  }
}
