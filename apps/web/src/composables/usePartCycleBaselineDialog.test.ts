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

vi.mock('../utils/partCyclePrecision', () => ({
  normalizePartCycleDays: (v: number) => Math.round(v),
  normalizePartUnitCycleDays: (v: number) => Math.round(v * 10) / 10,
}))

describe('usePartCycleBaselineDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const resolvePartType = (row: any) => row.core_part_name || row.part_type || ''

  it('initial state: dialog closed, form with defaults', async () => {
    const { usePartCycleBaselineDialog } = await import('./usePartCycleBaselineDialog')
    const { dialogVisible, isEdit, submitting, form } = usePartCycleBaselineDialog({
      resolvePartType,
      onSubmitted: vi.fn(),
    })

    expect(dialogVisible.value).toBe(false)
    expect(isEdit.value).toBe(false)
    expect(submitting.value).toBe(false)
    expect(form.part_type).toBe('')
    expect(form.ref_batch_qty).toBe(1)
    expect(form.cycle_days).toBe(30)
    expect(form.unit_cycle_days).toBe(1)
    expect(form.is_active).toBe(true)
  })

  it('handleAdd resets form and opens dialog in add mode', async () => {
    const { usePartCycleBaselineDialog } = await import('./usePartCycleBaselineDialog')
    const { dialogVisible, isEdit, form, handleAdd } = usePartCycleBaselineDialog({
      resolvePartType,
      onSubmitted: vi.fn(),
    })

    form.part_type = 'OLD'
    handleAdd()

    expect(dialogVisible.value).toBe(true)
    expect(isEdit.value).toBe(false)
    expect(form.part_type).toBe('')
  })

  it('handleEdit populates form from row using resolvePartType', async () => {
    const { usePartCycleBaselineDialog } = await import('./usePartCycleBaselineDialog')
    const { dialogVisible, isEdit, form, handleEdit } = usePartCycleBaselineDialog({
      resolvePartType,
      onSubmitted: vi.fn(),
    })

    handleEdit({
      id: 10,
      part_type: 'SHAFT',
      core_part_name: '主轴',
      material_no: 'MAT-001',
      material_desc: '主轴零件',
      machine_model: 'CNC-100',
      plant: 'P1',
      ref_batch_qty: 5,
      cycle_days: 15,
      unit_cycle_days: 3.2,
      match_rule: 'exact',
      confidence_level: 'high',
      is_active: true,
      remark: '测试',
    } as any)

    expect(dialogVisible.value).toBe(true)
    expect(isEdit.value).toBe(true)
    expect(form.id).toBe(10)
    expect(form.part_type).toBe('主轴') // resolvePartType uses core_part_name
    expect(form.material_desc).toBe('主轴零件')
    expect(form.machine_model).toBe('CNC-100')
    expect(form.ref_batch_qty).toBe(5)
  })

  it('handleSubmit posts data, shows success, and calls onSubmitted', async () => {
    const onSubmitted = vi.fn().mockResolvedValue(undefined)
    postMock.mockResolvedValueOnce({})

    const { usePartCycleBaselineDialog } = await import('./usePartCycleBaselineDialog')
    const { form, handleSubmit, dialogVisible } = usePartCycleBaselineDialog({
      resolvePartType,
      onSubmitted,
    })

    form.part_type = '主轴'
    form.material_desc = '零件A'
    form.machine_model = 'CNC-200'
    form.ref_batch_qty = 10
    form.cycle_days = 20
    form.unit_cycle_days = 2.5
    dialogVisible.value = true

    await handleSubmit()

    expect(postMock).toHaveBeenCalledWith('/api/admin/part-cycle-baselines', expect.objectContaining({
      part_type: '主轴',
      material_desc: '零件A',
      machine_model: 'CNC-200',
      ref_batch_qty: 10,
      cycle_days: 20,
      unit_cycle_days: 2.5,
    }))
    expect(successMock).toHaveBeenCalledWith('新增成功')
    expect(dialogVisible.value).toBe(false)
    expect(onSubmitted).toHaveBeenCalled()
  })

  it('handleSubmit shows 编辑成功 when in edit mode', async () => {
    const onSubmitted = vi.fn().mockResolvedValue(undefined)
    postMock.mockResolvedValueOnce({})

    const { usePartCycleBaselineDialog } = await import('./usePartCycleBaselineDialog')
    const { handleEdit, handleSubmit } = usePartCycleBaselineDialog({
      resolvePartType,
      onSubmitted,
    })

    handleEdit({
      id: 5,
      part_type: 'SHAFT',
      material_no: 'M1',
      material_desc: '零件B',
      ref_batch_qty: 1,
      cycle_days: 10,
      unit_cycle_days: 1,
      is_active: true,
    } as any)

    await handleSubmit()
    expect(successMock).toHaveBeenCalledWith('编辑成功')
  })

  it('handleSubmit handles API error without crashing', async () => {
    postMock.mockRejectedValueOnce(new Error('网络错误'))

    const { usePartCycleBaselineDialog } = await import('./usePartCycleBaselineDialog')
    const { handleSubmit, submitting, dialogVisible } = usePartCycleBaselineDialog({
      resolvePartType,
      onSubmitted: vi.fn(),
    })

    dialogVisible.value = true
    await handleSubmit()

    expect(submitting.value).toBe(false)
    expect(dialogVisible.value).toBe(true)
  })

  it('rules require key fields', async () => {
    const { usePartCycleBaselineDialog } = await import('./usePartCycleBaselineDialog')
    const { rules } = usePartCycleBaselineDialog({ resolvePartType, onSubmitted: vi.fn() })

    expect(rules.part_type).toBeDefined()
    expect(rules.material_desc).toBeDefined()
    expect(rules.machine_model).toBeDefined()
    expect(rules.ref_batch_qty).toBeDefined()
    expect(rules.cycle_days).toBeDefined()
    expect(rules.unit_cycle_days).toBeDefined()
  })
})
