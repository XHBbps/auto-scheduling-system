import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const postMock = vi.fn()
const deleteMock = vi.fn()
const pushMock = vi.fn()
const successMessageMock = vi.fn()
const confirmMock = vi.fn()

vi.mock('../utils/httpClient', () => ({
  default: {
    get: getMock,
    post: postMock,
    delete: deleteMock,
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  useRoute: () => ({
    fullPath: '/admin/machine-cycle',
  }),
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: successMessageMock,
      warning: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
    },
    ElMessageBox: {
      confirm: confirmMock,
    },
  }
})

const buildWrapper = async () => {
  const { useMachineCycleBaselinePage } = await import('./useMachineCycleBaselinePage')
  const TestComponent = defineComponent({
    setup() {
      return useMachineCycleBaselinePage()
    },
    template: '<div />',
  })
  const wrapper = mount(TestComponent)
  await flushPromises()
  return wrapper
}

describe('useMachineCycleBaselinePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getMock.mockResolvedValue({
      total: 0,
      page_no: 1,
      page_size: 10,
      items: [],
    })
    postMock.mockResolvedValue({ groups_processed: 3, total_samples: 12 })
    deleteMock.mockResolvedValue({})
    confirmMock.mockResolvedValue('confirm')
  })

  it('fills form and opens dialog when editing a row', async () => {
    const wrapper = await buildWrapper()

    wrapper.vm.handleEdit({
      id: 2,
      machine_model: 'MX-100',
      product_series: 'S1',
      order_qty: 2,
      cycle_days_median: 5,
      sample_count: 8,
      is_active: true,
      remark: '测试',
    })

    expect(wrapper.vm.dialogVisible).toBe(true)
    expect(wrapper.vm.isEdit).toBe(true)
    expect(wrapper.vm.form.machine_model).toBe('MX-100')
    expect(wrapper.vm.form.order_qty).toBe(2)
  })

  it('confirms rebuild request and shows success feedback', async () => {
    const wrapper = await buildWrapper()

    await wrapper.vm.handleRebuild()

    expect(confirmMock).toHaveBeenCalledWith(
      expect.anything(),
      '确认重建基准',
      expect.objectContaining({
        confirmButtonText: '确认重建',
      }),
    )
    expect(postMock).toHaveBeenCalledWith('/api/admin/machine-cycle-baselines/rebuild')
    expect(successMessageMock).toHaveBeenCalledWith('重建完成：3组 / 12条样本')
  })

  it('confirms and deletes a row successfully', async () => {
    const wrapper = await buildWrapper()

    await wrapper.vm.handleDelete({
      id: 8,
      machine_model: 'MX-200',
      product_series: 'S2',
      order_qty: 3,
      cycle_days_median: 6,
      sample_count: 10,
      is_active: true,
    })

    expect(confirmMock).toHaveBeenCalledWith(
      expect.anything(),
      '删除确认',
      expect.objectContaining({
        confirmButtonText: '确认删除',
      }),
    )
    expect(deleteMock).toHaveBeenCalledWith('/api/admin/machine-cycle-baselines/8')
    expect(successMessageMock).toHaveBeenCalledWith('删除成功')
  })
})

