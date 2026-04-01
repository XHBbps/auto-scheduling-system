import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const createAdminRoleMock = vi.fn()
const createAdminUserMock = vi.fn()
const deleteAdminRoleMock = vi.fn()
const getAdminRoleDetailMock = vi.fn()
const getAdminUserDetailMock = vi.fn()
const listAdminPermissionsMock = vi.fn()
const listAdminRolesMock = vi.fn()
const listAdminUsersMock = vi.fn()
const resetAdminUserPasswordMock = vi.fn()
const updateAdminRoleMock = vi.fn()
const updateAdminRoleStatusMock = vi.fn()
const updateAdminUserMock = vi.fn()
const updateAdminUserRolesMock = vi.fn()
const updateAdminUserStatusMock = vi.fn()

const successMessageMock = vi.fn()
const warningMessageMock = vi.fn()
const errorMessageMock = vi.fn()
const confirmMock = vi.fn()

const currentSessionState = {
  authenticated: true,
  user: {
    id: 1,
    username: 'admin',
    display_name: '系统管理员',
    is_active: true,
    roles: [{ code: 'admin', name: '管理员' }],
    permission_codes: ['user.view', 'user.manage', 'role.view', 'role.manage', 'permission.view'],
  },
  expiresAt: '2026-03-27T12:00:00Z',
  expiresAtMs: Date.now() + 60 * 60 * 1000,
  roleCodes: ['admin'],
  roleNames: ['管理员'],
  permissionCodes: ['user.view', 'user.manage', 'role.view', 'role.manage', 'permission.view'],
}

const hasAccessRequirementMock = vi.fn((state: any, requirement: any = {}) => {
  if (!state?.authenticated) return false
  const roleCodes = state.roleCodes || []
  const permissionCodes = state.permissionCodes || []
  if (roleCodes.includes('admin')) return true
  const requiredRoles = requirement.requiredRoles || []
  const requiredPermissions = requirement.requiredPermissions || []
  const requiredAnyPermissions = requirement.requiredAnyPermissions || []
  const matchesRoles = requiredRoles.every((role: string) => roleCodes.includes(role))
  const matchesPermissions = requiredPermissions.every((permission: string) => permissionCodes.includes(permission))
  const matchesAnyPermissions = !requiredAnyPermissions.length || requiredAnyPermissions.some((permission: string) => permissionCodes.includes(permission))
  return matchesRoles && matchesPermissions && matchesAnyPermissions
})

vi.mock('../api/userManagement', () => ({
  createAdminRole: createAdminRoleMock,
  createAdminUser: createAdminUserMock,
  deleteAdminRole: deleteAdminRoleMock,
  getAdminRoleDetail: getAdminRoleDetailMock,
  getAdminUserDetail: getAdminUserDetailMock,
  listAdminPermissions: listAdminPermissionsMock,
  listAdminRoles: listAdminRolesMock,
  listAdminUsers: listAdminUsersMock,
  resetAdminUserPassword: resetAdminUserPasswordMock,
  updateAdminRole: updateAdminRoleMock,
  updateAdminRoleStatus: updateAdminRoleStatusMock,
  updateAdminUser: updateAdminUserMock,
  updateAdminUserRoles: updateAdminUserRolesMock,
  updateAdminUserStatus: updateAdminUserStatusMock,
}))

vi.mock('../utils/authSession', () => ({
  AUTH_CHANGED_EVENT_NAME: 'auth-session-changed',
  formatAuthSessionExpiresAtDisplay: vi.fn((value?: string | null) => value || null),
  getAuthSessionState: vi.fn(() => currentSessionState),
}))

vi.mock('../utils/accessControl', () => ({
  hasAccessRequirement: hasAccessRequirementMock,
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: successMessageMock,
      warning: warningMessageMock,
      error: errorMessageMock,
      info: vi.fn(),
    },
    ElMessageBox: {
      confirm: confirmMock,
    },
  }
})

const buildWrapper = async () => {
  const { useUserManagementPage } = await import('./useUserManagementPage')

  const TestComponent = defineComponent({
    setup() {
      return useUserManagementPage()
    },
    template: '<div />',
  })

  const wrapper = mount(TestComponent)
  await flushPromises()
  return wrapper
}

describe('useUserManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    currentSessionState.authenticated = true
    currentSessionState.roleCodes = ['admin']
    currentSessionState.roleNames = ['管理员']
    currentSessionState.permissionCodes = ['user.view', 'user.manage', 'role.view', 'role.manage', 'permission.view']
    currentSessionState.user.roles = [{ code: 'admin', name: '管理员' }]
    currentSessionState.user.permission_codes = ['user.view', 'user.manage', 'role.view', 'role.manage', 'permission.view']

    listAdminUsersMock.mockResolvedValue({
      total: 1,
      page_no: 1,
      page_size: 20,
      items: [
        {
          id: 1,
          username: 'admin',
          display_name: '系统管理员',
          is_active: true,
          roles: [{ code: 'admin', name: '管理员' }],
          updated_at: '2026-03-26T00:00:00Z',
        },
      ],
    })
    listAdminRolesMock.mockResolvedValue({
      items: [
        {
          id: 1,
          code: 'admin',
          name: '管理员',
          description: '系统管理员',
          is_active: true,
          is_system: true,
          assigned_user_count: 1,
          permission_count: 10,
        },
        {
          id: 2,
          code: 'planner',
          name: '计划员',
          description: '排产计划',
          is_active: true,
          is_system: false,
          assigned_user_count: 0,
          permission_count: 3,
        },
      ],
    })
    listAdminPermissionsMock.mockResolvedValue({ items: [] })
    confirmMock.mockResolvedValue('confirm')
    resetAdminUserPasswordMock.mockResolvedValue({})
    updateAdminUserRolesMock.mockResolvedValue({})
  })

  it('loads only users on mount when the session only has user.view', async () => {
    currentSessionState.roleCodes = []
    currentSessionState.roleNames = []
    currentSessionState.permissionCodes = ['user.view']
    currentSessionState.user.roles = []
    currentSessionState.user.permission_codes = ['user.view']

    await buildWrapper()

    expect(listAdminUsersMock).toHaveBeenCalledTimes(1)
    expect(listAdminRolesMock).not.toHaveBeenCalled()
    expect(listAdminPermissionsMock).not.toHaveBeenCalled()
  })

  it('loads and refreshes only roles on the roles tab when the session only has role.view', async () => {
    currentSessionState.roleCodes = []
    currentSessionState.roleNames = []
    currentSessionState.permissionCodes = ['role.view']
    currentSessionState.user.roles = []
    currentSessionState.user.permission_codes = ['role.view']

    const wrapper = await buildWrapper()

    expect(wrapper.vm.activeTab).toBe('roles')
    expect(listAdminRolesMock).toHaveBeenCalledTimes(1)
    expect(listAdminUsersMock).not.toHaveBeenCalled()
    expect(listAdminPermissionsMock).not.toHaveBeenCalled()

    await wrapper.vm.refreshCurrentTab()

    expect(listAdminRolesMock).toHaveBeenCalledTimes(2)
    expect(listAdminPermissionsMock).not.toHaveBeenCalled()
  })

  it('requires role.view before exposing create-user capability', async () => {
    currentSessionState.roleCodes = []
    currentSessionState.roleNames = []
    currentSessionState.permissionCodes = ['user.view', 'user.manage']
    currentSessionState.user.roles = []
    currentSessionState.user.permission_codes = ['user.view', 'user.manage']

    const wrapper = await buildWrapper()

    expect(wrapper.vm.canCreateUser).toBe(false)
    expect(wrapper.vm.canAssignUserRoles).toBe(false)
    expect(listAdminRolesMock).not.toHaveBeenCalled()
  })

  it('warns when reset password is submitted without a new password', async () => {
    const wrapper = await buildWrapper()

    wrapper.vm.openResetPasswordDialog({
      id: 1,
      username: 'admin',
      display_name: '系统管理员',
      is_active: true,
      roles: [{ code: 'admin', name: '管理员' }],
    })
    await wrapper.vm.submitResetPassword()

    expect(warningMessageMock).toHaveBeenCalledWith('请输入新密码')
    expect(confirmMock).not.toHaveBeenCalled()
    expect(resetAdminUserPasswordMock).not.toHaveBeenCalled()
  }, 10000)

  it('confirms and resets password successfully', async () => {
    const wrapper = await buildWrapper()

    wrapper.vm.openResetPasswordDialog({
      id: 1,
      username: 'admin',
      display_name: '系统管理员',
      is_active: true,
      roles: [{ code: 'admin', name: '管理员' }],
    })
    wrapper.vm.passwordDialog.new_password = 'Soul@2026!'

    await wrapper.vm.submitResetPassword()

    expect(resetAdminUserPasswordMock).toHaveBeenCalledWith(1, {
      new_password: 'Soul@2026!',
    })
    expect(successMessageMock).toHaveBeenCalledWith('密码已重置')
    expect(wrapper.vm.passwordDialog.visible).toBe(false)
  })

  it('confirms and updates assigned roles successfully', async () => {
    const wrapper = await buildWrapper()

    wrapper.vm.openRoleAssignDialog({
      id: 2,
      username: 'planner',
      display_name: '计划员A',
      is_active: true,
      roles: [{ code: 'planner', name: '计划员' }],
    })
    wrapper.vm.roleAssignDialog.role_codes = ['admin', 'planner']

    await wrapper.vm.submitRoleAssign()

    expect(updateAdminUserRolesMock).toHaveBeenCalledWith(2, {
      role_codes: ['admin', 'planner'],
    })
    expect(successMessageMock).toHaveBeenCalledWith('角色分配已更新')
    expect(wrapper.vm.roleAssignDialog.visible).toBe(false)
  })
})
