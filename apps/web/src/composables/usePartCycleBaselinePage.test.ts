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
    fullPath: '/admin/part-cycle',
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
  const { usePartCycleBaselinePage } = await import('./usePartCycleBaselinePage')
  const TestComponent = defineComponent({
    setup() {
      return usePartCycleBaselinePage()
    },
    template: '<div />',
  })
  const wrapper = mount(TestComponent)
  await flushPromises()
  return wrapper
}

describe('usePartCycleBaselinePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getMock.mockResolvedValue([])
    postMock.mockResolvedValue({ message: '零件周期基准重建任务已触发' })
    deleteMock.mockResolvedValue({})
    confirmMock.mockResolvedValue('confirm')
  })

  it('fills form and opens dialog when editing a row', async () => {
    const wrapper = await buildWrapper()

    wrapper.vm.handleEdit({
      id: 1,
      part_type: '钣金件',
      material_no: 'MAT-001',
      material_desc: '测试零件',
      machine_model: 'M-01',
      plant: '1000',
      ref_batch_qty: 2,
      cycle_days: 3,
      unit_cycle_days: 1.5,
      match_rule: '按机型',
      confidence_level: '高',
      is_active: true,
      remark: '备注',
    })

    expect(wrapper.vm.dialogVisible).toBe(true)
    expect(wrapper.vm.isEdit).toBe(true)
    expect(wrapper.vm.form.part_type).toBe('钣金件')
    expect(wrapper.vm.form.plant).toBe('1000')
  })




it('normalizes cycle precision when editing and submitting', async () => {
  const wrapper = await buildWrapper()

  wrapper.vm.handleEdit({
    id: 11,
    part_type: '平衡缸',
    material_no: 'MAT-011',
    material_desc: '平衡缸总成',
    machine_model: 'M-11',
    plant: '1100',
    ref_batch_qty: 2,
    cycle_days: 12.6,
    unit_cycle_days: 1.26,
    is_active: true,
  })

  expect(wrapper.vm.form.cycle_days).toBe(13)
  expect(wrapper.vm.form.unit_cycle_days).toBe(1.3)

  wrapper.vm.form.cycle_days = 9.8
  wrapper.vm.form.unit_cycle_days = 0.66

  await wrapper.vm.handleSubmit()

  expect(postMock).toHaveBeenCalledWith(
    '/api/admin/part-cycle-baselines',
    expect.objectContaining({
      id: 11,
      cycle_days: 10,
      unit_cycle_days: 0.7,
    }),
  )
  expect(wrapper.vm.form.cycle_days).toBe(10)
  expect(wrapper.vm.form.unit_cycle_days).toBe(0.7)
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
    expect(postMock).toHaveBeenCalledWith('/api/admin/part-cycle-baselines/rebuild', {})
    expect(successMessageMock).toHaveBeenCalledWith('零件周期基准重建任务已触发')
  })

  it('confirms and deletes a row successfully', async () => {
    const wrapper = await buildWrapper()

    await wrapper.vm.handleDelete({
      id: 3,
      part_type: '机加件',
      material_no: 'MAT-003',
      material_desc: '待删除',
      machine_model: 'M-03',
      plant: null,
      ref_batch_qty: 1,
      cycle_days: 4,
      unit_cycle_days: 1,
      is_active: true,
    })

    expect(confirmMock).toHaveBeenCalledWith(
      expect.anything(),
      '删除确认',
      expect.objectContaining({
        confirmButtonText: '确认删除',
      }),
    )
    expect(deleteMock).toHaveBeenCalledWith('/api/admin/part-cycle-baselines/3')
    expect(successMessageMock).toHaveBeenCalledWith('删除成功')
  })
})
