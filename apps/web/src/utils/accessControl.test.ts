import { describe, expect, it } from 'vitest'
import { getRouteAccessRequirement, hasAccessRequirement, hasAnyPermissionCode, hasPermissionCode } from './accessControl'
import type { AuthSessionState } from './authSession'

const createState = (overrides?: Partial<AuthSessionState>): AuthSessionState => ({
  authenticated: true,
  user: null,
  expiresAt: null,
  expiresAtMs: null,
  roleCodes: ['planner'],
  roleNames: ['计划员'],
  permissionCodes: ['schedule.manage', 'sync.log.view'],
  ...overrides,
})

describe('accessControl', () => {
  it('accepts permissions for admin sessions', () => {
    expect(hasPermissionCode(createState({ roleCodes: ['admin'] }), 'user.manage')).toBe(true)
  })

  it('checks permission codes and access requirements', () => {
    const state = createState()
    expect(hasPermissionCode(state, 'schedule.manage')).toBe(true)
    expect(hasAnyPermissionCode(state, ['foo.bar', 'sync.log.view'])).toBe(true)
    expect(hasAccessRequirement(state, { requiredPermissions: ['schedule.manage'] })).toBe(true)
    expect(hasAccessRequirement(state, { requiredAnyPermissions: ['user.manage', 'sync.log.view'] })).toBe(true)
    expect(hasAccessRequirement(state, { requiredPermissions: ['user.manage'] })).toBe(false)
  })

  it('extracts route access requirement from route meta', () => {
    expect(getRouteAccessRequirement({ requiredRoles: ['admin'], requiredPermissions: ['sync.manage'], requiredAnyPermissions: ['user.view', 'role.view'] })).toEqual({
      requiredRoles: ['admin'],
      requiredPermissions: ['sync.manage'],
      requiredAnyPermissions: ['user.view', 'role.view'],
    })
  })
})
