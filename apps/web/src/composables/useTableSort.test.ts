import { describe, expect, it } from 'vitest'
import {
  applyLocalSort,
  DEFAULT_TABLE_SORT_ORDERS,
  getTableSortColumnProps,
  useTableSort,
} from './useTableSort'

describe('useTableSort', () => {
  it('初始状态为空', () => {
    const { sortField, sortOrder, buildSortParams } = useTableSort()

    expect(sortField.value).toBeUndefined()
    expect(sortOrder.value).toBeUndefined()
    expect(buildSortParams()).toEqual({})
  })

  it('accepts initial state', () => {
    const { sortField, sortOrder, buildSortParams } = useTableSort({
      sortField: 'name',
      sortOrder: 'asc',
    })

    expect(sortField.value).toBe('name')
    expect(sortOrder.value).toBe('asc')
    expect(buildSortParams()).toEqual({ sort_field: 'name', sort_order: 'asc' })
  })

  it('handleSortChange normalizes element-plus order', () => {
    const { sortField, sortOrder, handleSortChange, buildSortParams } = useTableSort()

    handleSortChange({ prop: 'age', order: 'ascending' })
    expect(sortField.value).toBe('age')
    expect(sortOrder.value).toBe('asc')
    expect(buildSortParams()).toEqual({ sort_field: 'age', sort_order: 'asc' })

    handleSortChange({ prop: 'age', order: 'descending' })
    expect(sortOrder.value).toBe('desc')

    handleSortChange({ prop: 'age', order: null })
    expect(sortOrder.value).toBeUndefined()
    expect(buildSortParams()).toEqual({})
  })

  it('resetSort clears state', () => {
    const { sortField, sortOrder, handleSortChange, resetSort } = useTableSort()

    handleSortChange({ prop: 'name', order: 'ascending' })
    resetSort()

    expect(sortField.value).toBeUndefined()
    expect(sortOrder.value).toBeUndefined()
  })
})

describe('applyLocalSort', () => {
  const data = [
    { name: 'Charlie', age: 30 },
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 35 },
  ]

  it('returns a shallow copy when no sort state', () => {
    const result = applyLocalSort(data, {})
    expect(result).toEqual(data)
    expect(result).not.toBe(data)
  })

  it('sorts ascending by string field', () => {
    const result = applyLocalSort(data, { sortField: 'name', sortOrder: 'asc' })
    expect(result.map((r) => r.name)).toEqual(['Alice', 'Bob', 'Charlie'])
  })

  it('sorts descending by numeric field', () => {
    const result = applyLocalSort(data, { sortField: 'age', sortOrder: 'desc' })
    expect(result.map((r) => r.age)).toEqual([35, 30, 25])
  })

  it('handles null values by pushing them to end', () => {
    const withNulls = [
      { name: 'Alice', value: null },
      { name: 'Bob', value: 10 },
      { name: 'Charlie', value: 5 },
    ]
    const result = applyLocalSort(withNulls, { sortField: 'value', sortOrder: 'asc' })
    expect(result.map((r) => r.value)).toEqual([5, 10, null])
  })

  it('keeps sticky-bottom rows at bottom', () => {
    const items = [
      { id: 1, name: 'Charlie', sticky: true },
      { id: 2, name: 'Alice', sticky: false },
      { id: 3, name: 'Bob', sticky: false },
    ]
    const result = applyLocalSort(items, { sortField: 'name', sortOrder: 'asc' }, {
      isStickyBottom: (row) => row.sticky,
    })
    expect(result.map((r) => r.name)).toEqual(['Alice', 'Bob', 'Charlie'])
  })

  it('sorts date-like strings correctly', () => {
    const items = [
      { date: '2026-03-15' },
      { date: '2026-01-10' },
      { date: '2026-06-20' },
    ]
    const result = applyLocalSort(items, { sortField: 'date', sortOrder: 'asc' })
    expect(result.map((r) => r.date)).toEqual(['2026-01-10', '2026-03-15', '2026-06-20'])
  })
})

describe('getTableSortColumnProps', () => {
  it('returns custom sortable and sort-orders', () => {
    const props = getTableSortColumnProps()
    expect(props.sortable).toBe('custom')
    expect(props['sort-orders']).toBe(DEFAULT_TABLE_SORT_ORDERS)
  })
})
