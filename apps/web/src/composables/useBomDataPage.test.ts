import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()

vi.mock('../utils/httpClient', () => ({
  default: {
    get: getMock,
  },
}))

vi.mock('../utils/format', () => ({
  cleanParams: (params: Record<string, any>) => {
    const cleaned: Record<string, any> = {}
    Object.keys(params).forEach((key) => {
      if (params[key] !== '' && params[key] !== null && params[key] !== undefined) {
        cleaned[key] = params[key]
      }
    })
    return cleaned
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ fullPath: '/admin/bom-data' }),
}))

const createTreeResponse = () => ({
  total: 2,
  root_count: 2,
  roots: [
    {
      id: 1,
      node_key: 'root-1',
      machine_material_no: 'M001',
      material_no: 'MAT-001',
      material_desc: 'Machine A',
      is_top_level: true,
      is_self_made: false,
      has_children: true,
      children_loaded: false,
      children: [],
    },
    {
      id: 2,
      node_key: 'root-2',
      machine_material_no: 'M002',
      material_no: 'MAT-002',
      material_desc: 'Machine B',
      is_top_level: true,
      is_self_made: false,
      has_children: false,
      children_loaded: true,
      children: [],
    },
  ],
})

const createListResponse = () => ({
  total: 1,
  page_no: 1,
  page_size: 10,
  items: [
    {
      id: 10,
      machine_material_no: 'M001',
      material_no: 'MAT-001',
      is_top_level: true,
      is_self_made: false,
    },
  ],
})

const buildWrapper = async () => {
  const { useBomDataPage } = await import('./useBomDataPage')
  const TestComponent = defineComponent({
    setup() {
      return useBomDataPage()
    },
    template: '<div />',
  })
  const wrapper = mount(TestComponent)
  await flushPromises()
  return wrapper
}

describe('useBomDataPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads tree data on mount when activeTab is tree', async () => {
    getMock.mockResolvedValueOnce(createTreeResponse())

    const wrapper = await buildWrapper()

    expect(getMock).toHaveBeenCalledTimes(1)
    expect(getMock).toHaveBeenCalledWith('/api/data/bom-relations/tree', expect.any(Object))
    expect(wrapper.vm.pagedTreeTableData.length).toBe(2)
    expect(wrapper.vm.treeLoading).toBe(false)
  })

  it('handles tree fetch error gracefully', async () => {
    getMock.mockRejectedValueOnce(new Error('网络错误'))

    const wrapper = await buildWrapper()

    expect(wrapper.vm.pagedTreeTableData.length).toBe(0)
    expect(wrapper.vm.treeLoading).toBe(false)
  })

  it('handleTreeReset clears form and reloads', async () => {
    getMock.mockResolvedValueOnce(createTreeResponse())
    const wrapper = await buildWrapper()

    wrapper.vm.treeForm.machine_material_no = 'M001'
    getMock.mockResolvedValueOnce(createTreeResponse())
    wrapper.vm.handleTreeReset()
    await flushPromises()

    expect(wrapper.vm.treeForm.machine_material_no).toBe('')
    expect(getMock).toHaveBeenCalledTimes(2)
  })

  it('fetches list data when handleListSearch is called', async () => {
    getMock.mockResolvedValueOnce(createTreeResponse())
    const wrapper = await buildWrapper()

    getMock.mockResolvedValueOnce(createListResponse())
    wrapper.vm.handleListSearch()
    await flushPromises()

    expect(wrapper.vm.listTableData).toHaveLength(1)
    expect(wrapper.vm.total).toBe(1)
    expect(wrapper.vm.pageNo).toBe(1)
  })

  it('handleListReset clears list form and reloads', async () => {
    getMock.mockResolvedValueOnce(createTreeResponse())
    const wrapper = await buildWrapper()

    wrapper.vm.listForm.machine_material_no = 'X'
    getMock.mockResolvedValueOnce(createListResponse())
    wrapper.vm.handleListReset()
    await flushPromises()

    expect(wrapper.vm.listForm.machine_material_no).toBe('')
  })
})
