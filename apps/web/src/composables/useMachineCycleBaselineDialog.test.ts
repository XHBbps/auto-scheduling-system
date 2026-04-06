import { beforeEach, describe, expect, it, vi } from 'vitest'

const postMock = vi.fn()
const successMock = vi.fn()

vi.mock('../utils/httpClient', () => ({
  default: {
    post: postMock,
  },
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: successMock,
  },
}))

describe('useMachineCycleBaselineDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initial state: dialog closed, not editing, not submitting', async () => {
    const { useMachineCycleBaselineDialog } = await import('./useMachineCycleBaselineDialog')
    const { dialogVisible, isEdit, submitting, form } = useMachineCycleBaselineDialog({
      onSubmitted: vi.fn(),
    })

    expect(dialogVisible.value).toBe(false)
    expect(isEdit.value).toBe(false)
    expect(submitting.value).toBe(false)
    expect(form.machine_model).toBe('')
    expect(form.order_qty).toBe(1)
    expect(form.cycle_days_median).toBe(30)
    expect(form.is_active).toBe(true)
  })

  it('handleAdd resets form and opens dialog in add mode', async () => {
    const { useMachineCycleBaselineDialog } = await import('./useMachineCycleBaselineDialog')
    const { dialogVisible, isEdit, form, handleAdd } = useMachineCycleBaselineDialog({
      onSubmitted: vi.fn(),
    })

    form.machine_model = 'OLD_VALUE'
    handleAdd()

    expect(dialogVisible.value).toBe(true)
    expect(isEdit.value).toBe(false)
    expect(form.machine_model).toBe('')
  })

  it('handleEdit populates form from row and sets edit mode', async () => {
    const { useMachineCycleBaselineDialog } = await import('./useMachineCycleBaselineDialog')
    const { dialogVisible, isEdit, form, handleEdit } = useMachineCycleBaselineDialog({
      onSubmitted: vi.fn(),
    })

    handleEdit({
      id: 1,
      machine_model: 'CNC-100',
      product_series: 'S1',
      order_qty: 5,
      cycle_days_median: 45,
      sample_count: 10,
      is_active: false,
      remark: '测试备注',
    })

    expect(dialogVisible.value).toBe(true)
    expect(isEdit.value).toBe(true)
    expect(form.machine_model).toBe('CNC-100')
    expect(form.product_series).toBe('S1')
    expect(form.order_qty).toBe(5)
    expect(form.cycle_days_median).toBe(45)
    expect(form.is_active).toBe(false)
    expect(form.remark).toBe('测试备注')
  })

  it('handleSubmit posts data, shows success message, and calls onSubmitted', async () => {
    const onSubmitted = vi.fn().mockResolvedValue(undefined)
    postMock.mockResolvedValueOnce({})

    const { useMachineCycleBaselineDialog } = await import('./useMachineCycleBaselineDialog')
    const { form, handleSubmit, dialogVisible, submitting } = useMachineCycleBaselineDialog({
      onSubmitted,
    })

    form.machine_model = 'CNC-200'
    form.order_qty = 3
    form.cycle_days_median = 20
    dialogVisible.value = true

    await handleSubmit()

    expect(postMock).toHaveBeenCalledWith('/api/admin/machine-cycle-baselines', expect.objectContaining({
      machine_model: 'CNC-200',
      order_qty: 3,
      cycle_days_median: 20,
    }))
    expect(successMock).toHaveBeenCalledWith('新增成功')
    expect(dialogVisible.value).toBe(false)
    expect(submitting.value).toBe(false)
    expect(onSubmitted).toHaveBeenCalled()
  })

  it('handleSubmit shows 编辑成功 when in edit mode', async () => {
    const onSubmitted = vi.fn().mockResolvedValue(undefined)
    postMock.mockResolvedValueOnce({})

    const { useMachineCycleBaselineDialog } = await import('./useMachineCycleBaselineDialog')
    const { handleEdit, handleSubmit } = useMachineCycleBaselineDialog({ onSubmitted })

    handleEdit({
      id: 1,
      machine_model: 'CNC-100',
      order_qty: 5,
      cycle_days_median: 45,
      sample_count: 10,
      is_active: true,
    })

    await handleSubmit()

    expect(successMock).toHaveBeenCalledWith('编辑成功')
  })

  it('handleSubmit handles API error without crashing', async () => {
    postMock.mockRejectedValueOnce(new Error('网络错误'))

    const { useMachineCycleBaselineDialog } = await import('./useMachineCycleBaselineDialog')
    const { handleSubmit, submitting, dialogVisible } = useMachineCycleBaselineDialog({
      onSubmitted: vi.fn(),
    })

    dialogVisible.value = true
    await handleSubmit()

    expect(submitting.value).toBe(false)
    // dialog stays open on error
    expect(dialogVisible.value).toBe(true)
  })

  it('rules require machine_model, order_qty, cycle_days_median', async () => {
    const { useMachineCycleBaselineDialog } = await import('./useMachineCycleBaselineDialog')
    const { rules } = useMachineCycleBaselineDialog({ onSubmitted: vi.fn() })

    expect(rules.machine_model).toBeDefined()
    expect(rules.order_qty).toBeDefined()
    expect(rules.cycle_days_median).toBeDefined()
  })
})
