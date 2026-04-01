import { onMounted, ref, watch } from 'vue'
import type { TableSortChange } from './useTableSort'
import { useLocalTablePagination } from './useTablePagination'
import { applyLocalSort, useTableSort } from './useTableSort'
import request from '../utils/httpClient'
import { cleanParams } from '../utils/format'

export interface BomItem {
  id: number
  machine_material_no: string
  machine_material_desc?: string
  plant?: string
  material_no?: string
  material_desc?: string
  bom_component_no?: string
  bom_component_desc?: string
  part_type?: string
  component_qty?: number
  bom_level?: number
  is_top_level: boolean
  is_self_made: boolean
  sync_time?: string
  created_at?: string
}

export interface BomTreeNode {
  id: number
  node_key: string
  machine_material_no: string
  plant?: string
  parent_material_no?: string | null
  parent_material_desc?: string | null
  material_no?: string
  material_desc?: string
  part_type?: string
  component_qty?: number
  bom_level?: number
  is_top_level: boolean
  is_self_made: boolean
  sync_time?: string
  created_at?: string | null
  has_children: boolean
  children_loaded: boolean
  children?: BomTreeNode[]
  is_load_more?: boolean
  parent_node_key?: string
  next_offset?: number
  loaded_children?: number
  total_children?: number
  loading_more?: boolean
}

interface PaginatedResponse {
  total: number
  page_no: number
  page_size: number
  items: BomItem[]
}

interface TreeResponse {
  total: number
  root_count: number
  root?: BomTreeNode | null
  roots: BomTreeNode[]
}

interface TreeChildrenResponse {
  total: number
  count?: number
  offset?: number
  limit?: number | null
  has_more?: boolean
  next_offset?: number
  items: BomTreeNode[]
}

const TREE_CHILD_PAGE_SIZE = 100

export const useBomDataPage = () => {
  const activeTab = ref<'tree' | 'list'>('tree')

  const treeForm = ref({ machine_material_no: '' })
  const treeLoading = ref(false)
  const treeRoots = ref<BomTreeNode[]>([])

  const listForm = ref({ machine_material_no: '', material_no: '', bom_component_no: '', part_type: '' })
  const listLoading = ref(false)
  const listTableData = ref<BomItem[]>([])
  const listLoaded = ref(false)
  const pageNo = ref(1)
  const pageSize = ref(10)
  const total = ref(0)

  const {
    sortField: treeSortField,
    sortOrder: treeSortOrder,
    handleSortChange: handleTreeSortBaseChange,
    resetSort: resetTreeSort,
  } = useTableSort()
  const { buildSortParams, handleSortChange: handleListSortBaseChange, resetSort: resetListSort } = useTableSort()
  const {
    pageNo: treePageNo,
    pageSize: treePageSize,
    pageSizes: treePageSizes,
    total: treeTotal,
    pagedData: pagedTreeTableData,
    resetPagination: resetTreePagination,
  } = useLocalTablePagination(() => treeRoots.value)

  const normalizeTreeNode = (node: BomTreeNode): BomTreeNode => ({
    ...node,
    has_children: !!node.has_children,
    children_loaded: !!node.children_loaded,
    is_load_more: !!node.is_load_more,
    loading_more: !!node.loading_more,
    children: Array.isArray(node.children) ? node.children.map(normalizeTreeNode) : [],
  })

  const isLoadMoreNode = (node?: BomTreeNode | null) => !!node?.is_load_more

  const createLoadMoreNode = (
    parent: BomTreeNode,
    nextOffset: number,
    loadedChildren: number,
    totalChildren: number,
  ): BomTreeNode => normalizeTreeNode({
    id: -1,
    node_key: `bom-load-more-${parent.node_key}-${nextOffset}`,
    machine_material_no: parent.machine_material_no,
    parent_material_no: parent.material_no,
    material_no: '',
    material_desc: '',
    part_type: '',
    component_qty: undefined,
    bom_level: undefined,
    is_top_level: false,
    is_self_made: false,
    has_children: false,
    children_loaded: true,
    children: [],
    is_load_more: true,
    parent_node_key: parent.node_key,
    next_offset: nextOffset,
    loaded_children: loadedChildren,
    total_children: totalChildren,
    loading_more: false,
  })

  const buildTreeChildren = (parent: BomTreeNode, res: TreeChildrenResponse): BomTreeNode[] => {
    const baseChildren = (res.items || []).map(normalizeTreeNode)
    if (!res.has_more) {
      return baseChildren
    }

    const loadedChildren = res.next_offset ?? ((res.offset ?? 0) + baseChildren.length)
    const totalChildren = res.total || loadedChildren
    return [
      ...baseChildren,
      createLoadMoreNode(parent, loadedChildren, loadedChildren, totalChildren),
    ]
  }

  const findTreeNodeByKey = (nodes: BomTreeNode[], nodeKey?: string): BomTreeNode | null => {
    if (!nodeKey) return null
    for (const node of nodes) {
      if (node.node_key === nodeKey) return node
      if (node.children?.length) {
        const matched = findTreeNodeByKey(node.children, nodeKey)
        if (matched) return matched
      }
    }
    return null
  }

  const sortTreeNodes = (nodes: BomTreeNode[]) => {
    const sortedNodes = applyLocalSort(
      nodes,
      {
        sortField: treeSortField.value,
        sortOrder: treeSortOrder.value,
      },
      {
        isStickyBottom: (row) => !!row.is_load_more,
      },
    )

    return sortedNodes.map((node) => {
      if (node.children?.length) {
        node.children = sortTreeNodes(node.children)
      }
      return node
    })
  }

  const applyTreeSort = () => {
    treeRoots.value = sortTreeNodes(treeRoots.value)
  }

  const getTreeQueryParams = () => cleanParams({ machine_material_no: treeForm.value.machine_material_no })
  const getListQueryParams = () => cleanParams({
    page_no: pageNo.value,
    page_size: pageSize.value,
    ...listForm.value,
    ...buildSortParams(),
  })

  const fetchTreeChildren = async (parent: BomTreeNode, offset = 0) => (
    request.get<TreeChildrenResponse>('/api/data/bom-relations/tree/children', {
      params: {
        machine_material_no: parent.machine_material_no,
        parent_material_no: parent.material_no,
        offset,
        limit: TREE_CHILD_PAGE_SIZE,
      },
    })
  )

  const fetchTreeData = async () => {
    treeLoading.value = true
    resetTreePagination()
    try {
      const res = await request.get<TreeResponse>('/api/data/bom-relations/tree', { params: getTreeQueryParams() })
      const roots = res.roots || (res.root ? [res.root] : [])
      treeRoots.value = roots.map(normalizeTreeNode)
      applyTreeSort()
    } catch (error) {
      console.error(error)
      treeRoots.value = []
    } finally {
      treeLoading.value = false
    }
  }

  const loadTreeNode = async (row: BomTreeNode, _treeNode: unknown, resolve: (data: BomTreeNode[]) => void) => {
    if (!row.has_children || isLoadMoreNode(row)) {
      resolve([])
      return
    }

    if (row.children_loaded) {
      resolve(row.children || [])
      return
    }

    try {
      const res = await fetchTreeChildren(row)
      const children = buildTreeChildren(row, res)
      row.children = children
      row.children_loaded = true
      applyTreeSort()
      resolve(row.children || [])
    } catch (error) {
      console.error(error)
      resolve([])
    }
  }

  const handleLoadMore = async (row: BomTreeNode) => {
    if (!row.is_load_more || row.loading_more) {
      return
    }

    const parent = findTreeNodeByKey(treeRoots.value, row.parent_node_key)
    if (!parent) {
      return
    }

    row.loading_more = true
    try {
      const res = await fetchTreeChildren(parent, row.next_offset || 0)
      const currentChildren = (parent.children || []).filter((item) => item.node_key !== row.node_key)
      parent.children = [...currentChildren, ...buildTreeChildren(parent, res)]
      applyTreeSort()
    } catch (error) {
      console.error(error)
    } finally {
      row.loading_more = false
    }
  }

  const fetchListData = async () => {
    listLoading.value = true
    try {
      const res = await request.get<PaginatedResponse>('/api/data/bom-relations', { params: getListQueryParams() })
      listTableData.value = res.items || []
      total.value = res.total || 0
      listLoaded.value = true
    } catch (error) {
      console.error(error)
    } finally {
      listLoading.value = false
    }
  }

  const handleTreeSearch = () => {
    resetTreePagination()
    void fetchTreeData()
  }

  const handleTreeReset = () => {
    treeForm.value.machine_material_no = ''
    resetTreeSort()
    resetTreePagination()
    void fetchTreeData()
  }

  const handleListSearch = () => {
    pageNo.value = 1
    void fetchListData()
  }

  const handleListReset = () => {
    listForm.value = { machine_material_no: '', material_no: '', bom_component_no: '', part_type: '' }
    resetListSort()
    handleListSearch()
  }

  const handleListSortChange = (sort: TableSortChange) => {
    handleListSortBaseChange(sort)
    pageNo.value = 1
    void fetchListData()
  }

  const handleTreeSortChange = (sort: TableSortChange) => {
    handleTreeSortBaseChange(sort)
    applyTreeSort()
  }

  onMounted(() => {
    if (activeTab.value === 'tree') {
      void fetchTreeData()
    } else {
      void fetchListData()
    }
  })

  watch(activeTab, (tab) => {
    if (tab === 'tree' && treeRoots.value.length === 0) {
      void fetchTreeData()
    }
    if (tab === 'list' && !listLoaded.value) {
      void fetchListData()
    }
  })

  return {
    activeTab,
    treeForm,
    treeLoading,
    treePageNo,
    treePageSize,
    treePageSizes,
    treeTotal,
    pagedTreeTableData,
    listForm,
    listLoading,
    listTableData,
    pageNo,
    pageSize,
    total,
    loadTreeNode,
    handleLoadMore,
    fetchListData,
    handleTreeSearch,
    handleTreeReset,
    handleListSearch,
    handleListReset,
    handleListSortChange,
    handleTreeSortChange,
  }
}
