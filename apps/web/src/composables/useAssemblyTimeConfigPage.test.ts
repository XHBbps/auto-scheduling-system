import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const postMock = vi.fn()
const deleteMock = vi.fn()
const successMessageMock = vi.fn()
const showStructuredConfirmDialogMock = vi.fn()

vi.mock('../utils/httpClient', () => ({
  default: {
    get: getMock,
    post: postMock,
    delete: deleteMock,
  },
}))

vi.mock('../utils/confirmDialog', () => ({
  showStructuredConfirmDialog: showStructuredConfirmDialogMock,
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
      confirm: vi.fn(),
    },
  }
})

const buildWrapper = async () => {
  const { useAssemblyTimeConfigPage } = await import('./useAssemblyTimeConfigPage')
  const TestComponent = defineComponent({
    setup() {
      return useAssemblyTimeConfigPage()
    },
    template: '<div />',
  })
  const wrapper = mount(TestComponent)
  await flushPromises()
  return wrapper
}

describe('useAssemblyTimeConfigPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    getMock.mockResolvedValue([])
    postMock.mockResolvedValue({})
    deleteMock.mockResolvedValue({})
    showStructuredConfirmDialogMock.mockResolvedValue('confirm')
  })

  it('opens edit dialog and hydrates form', async () => {
    const wrapper = await buildWrapper()

    wrapper.vm.handleEdit({
      id: 1,
      machine_model: 'MX-100',
      product_series: 'S1',
      assembly_name: '总装',
      assembly_time_days: 3,
      production_sequence: 1,
      is_final_assembly: true,
      is_default: false,
      remark: '备注',
    })

    expect(wrapper.vm.dialogVisible).toBe(true)
    expect(wrapper.vm.isEdit).toBe(true)
    expect(wrapper.vm.form.machine_model).toBe('MX-100')
    expect(wrapper.vm.form.assembly_name).toBe('总装')
  })

  it('auto marks 整机总装 as final assembly and suggests the next sequence', async () => {
    getMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: 10,
          machine_model: 'JH21-80',
          product_series: '开式压力机',
          assembly_name: '机身',
          assembly_time_days: 1,
          production_sequence: 1,
          is_final_assembly: false,
          is_default: true,
        },
        {
          id: 11,
          machine_model: 'JH21-80',
          product_series: '开式压力机',
          assembly_name: '电气',
          assembly_time_days: 1,
          production_sequence: 5,
          is_final_assembly: false,
          is_default: true,
        },
      ])

    const wrapper = await buildWrapper()

    wrapper.vm.handleAdd()
    wrapper.vm.form.machine_model = 'JH21-80'
    wrapper.vm.form.assembly_name = '整机总装'
    await nextTick()
    vi.runAllTimers()
    await flushPromises()

    expect(wrapper.vm.form.is_final_assembly).toBe(true)
    expect(wrapper.vm.form.production_sequence).toBe(6)
  })

  it('keeps final assembly sequence suggestion active when editing 整机总装', async () => {
    getMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: 10,
          machine_model: 'JH21-80',
          product_series: '开式压力机',
          assembly_name: '机身',
          assembly_time_days: 1,
          production_sequence: 1,
          is_final_assembly: false,
          is_default: true,
        },
        {
          id: 11,
          machine_model: 'JH21-80',
          product_series: '开式压力机',
          assembly_name: '电气',
          assembly_time_days: 1,
          production_sequence: 5,
          is_final_assembly: false,
          is_default: true,
        },
      ])

    const wrapper = await buildWrapper()

    wrapper.vm.handleEdit({
      id: 30,
      machine_model: 'JH21-80',
      product_series: '开式压力机',
      assembly_name: '整机总装',
      assembly_time_days: 3,
      production_sequence: 1,
      is_final_assembly: true,
      is_default: true,
      remark: '',
    })
    await nextTick()
    vi.runAllTimers()
    await flushPromises()

    expect(wrapper.vm.form.production_sequence).toBe(6)
  })

  it('confirms and deletes a row successfully', async () => {
    const wrapper = await buildWrapper()

    await wrapper.vm.handleDelete({
      id: 5,
      machine_model: 'MX-200',
      product_series: 'S2',
      assembly_name: '装配A',
      assembly_time_days: 2,
      production_sequence: 2,
      is_final_assembly: false,
      is_default: false,
      remark: undefined,
    })

    expect(showStructuredConfirmDialogMock).toHaveBeenCalledWith(
      expect.objectContaining({
        title: '删除确认',
        badge: '删除装配时长',
        headline: '确认删除【MX-200 / 装配A】这条记录吗？',
        confirmButtonText: '确认删除',
      }),
    )
    expect(deleteMock).toHaveBeenCalledWith('/api/admin/assembly-times/5')
    expect(successMessageMock).toHaveBeenCalledWith('删除成功')
  })
})
