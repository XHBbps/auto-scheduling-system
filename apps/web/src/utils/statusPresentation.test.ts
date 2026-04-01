import { describe, expect, it } from 'vitest'
import { getActiveStatusBadgeMeta, getSystemBuiltInBadgeMeta } from './statusPresentation'

describe('statusPresentation', () => {
  it('returns active/inactive badge metadata', () => {
    expect(getActiveStatusBadgeMeta(true)).toMatchObject({ label: '启用', tone: 'success' })
    expect(getActiveStatusBadgeMeta(false)).toMatchObject({ label: '停用', tone: 'neutral' })
  })

  it('returns system/custom badge metadata', () => {
    expect(getSystemBuiltInBadgeMeta(true)).toMatchObject({ label: '系统内置', tone: 'primary' })
    expect(getSystemBuiltInBadgeMeta(false)).toMatchObject({ label: '自定义', tone: 'neutral' })
  })
})
