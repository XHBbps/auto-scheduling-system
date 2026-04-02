import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createAdminRole,
  createAdminUser,
  deleteAdminRole,
  getAdminRoleDetail,
  getAdminUserDetail,
  listAdminPermissions,
  listAdminRoles,
  listAdminUsers,
  resetAdminUserPassword,
  updateAdminRole,
  updateAdminRoleStatus,
  updateAdminUser,
  updateAdminUserRoles,
  updateAdminUserStatus,
} from '../api/userManagement'
import type {
  AdminPermissionItem,
  AdminRoleDetail,
  AdminRoleItem,
  AdminUserDetail,
  AdminUserItem,
} from '../types/apiModels'
import { TABLE_PAGE_SIZE_OPTIONS, useLocalTablePagination } from './useTablePagination'
import { AUTH_CHANGED_EVENT_NAME, getAuthSessionState } from '../utils/authSession'
import { showStructuredConfirmDialog } from '../utils/confirmDialog'
import { formatDateTimeFull } from '../utils/format'
import { hasAccessRequirement } from '../utils/accessControl'

export type UserDialogMode = 'create' | 'edit'
export type RoleDialogMode = 'create' | 'edit'
export type AdminUserStatusFilter = '' | 'true' | 'false'
export type UserManagementActiveTab = 'users' | 'roles' | 'permissions'

export interface UserFiltersState {
  keyword: string
  role_code: string
  is_active: AdminUserStatusFilter
}

export interface PermissionFiltersState {
  keyword: string
  module_name: string
}

export interface UserPaginationState {
  total: number
  pageNo: number
  pageSize: number
}

export interface UserDialogState {
  visible: boolean
  mode: UserDialogMode
  editingId: number
  form: {
    username: string
    display_name: string
    password: string
    role_codes: string[]
    is_active: boolean
  }
}

export interface RoleAssignDialogState {
  visible: boolean
  userId: number
  userDisplayName: string
  role_codes: string[]
}

export interface PasswordDialogState {
  visible: boolean
  userId: number
  userDisplayName: string
  new_password: string
}

export interface RoleDialogState {
  visible: boolean
  mode: RoleDialogMode
  editingId: number
  loading: boolean
  form: {
    code: string
    name: string
    description: string
    is_active: boolean
  }
}

export interface UserDetailDrawerState {
  visible: boolean
  loading: boolean
  data: AdminUserDetail | null
}

export interface RoleDetailDrawerState {
  visible: boolean
  loading: boolean
  data: AdminRoleDetail | null
}

const confirmManagementAction = (options: {
  title: string
  badge: string
  headline: string
  description?: string
  confirmButtonText: string
}) =>
  showStructuredConfirmDialog({
    title: options.title,
    badge: options.badge,
    headline: options.headline,
    description: options.description,
    confirmButtonText: options.confirmButtonText,
    cancelButtonText: '取消',
    type: 'warning',
  })

export const useUserManagementPage = () => {
  const currentSessionState = ref(getAuthSessionState())
  const syncCurrentSessionState = () => {
    currentSessionState.value = getAuthSessionState()
  }

  const activeTab = ref<UserManagementActiveTab>('users')
  const refreshingCurrentTab = ref(false)
  const submitting = ref(false)

  const usersLoading = ref(false)
  const rolesLoading = ref(false)
  const permissionsLoading = ref(false)

  const userItems = ref<AdminUserItem[]>([])
  const roleOptions = ref<AdminRoleItem[]>([])
  const permissionItems = ref<AdminPermissionItem[]>([])

  const pageSizeOptions = [...TABLE_PAGE_SIZE_OPTIONS]

  const {
    pageNo: rolePageNo,
    pageSize: rolePageSize,
    total: roleTotal,
    pagedData: pagedRoleItems,
  } = useLocalTablePagination(() => roleOptions.value)

  const userPagination = reactive<UserPaginationState>({
    total: 0,
    pageNo: 1,
    pageSize: 20,
  })

  const userFilters = reactive<UserFiltersState>({
    keyword: '',
    role_code: '',
    is_active: '',
  })

  const permissionFilters = reactive<PermissionFiltersState>({
    keyword: '',
    module_name: '',
  })

  const userDialog = reactive<UserDialogState>({
    visible: false,
    mode: 'create',
    editingId: 0,
    form: {
      username: '',
      display_name: '',
      password: '',
      role_codes: [],
      is_active: true,
    },
  })

  const roleAssignDialog = reactive<RoleAssignDialogState>({
    visible: false,
    userId: 0,
    userDisplayName: '',
    role_codes: [],
  })

  const passwordDialog = reactive<PasswordDialogState>({
    visible: false,
    userId: 0,
    userDisplayName: '',
    new_password: '',
  })

  const roleDialog = reactive<RoleDialogState>({
    visible: false,
    mode: 'create',
    editingId: 0,
    loading: false,
    form: {
      code: '',
      name: '',
      description: '',
      is_active: true,
    },
  })

  const userDetailDrawer = reactive<UserDetailDrawerState>({
    visible: false,
    loading: false,
    data: null,
  })

  const roleDetailDrawer = reactive<RoleDetailDrawerState>({
    visible: false,
    loading: false,
    data: null,
  })

  const activeRoleOptions = computed(() => roleOptions.value.filter((role) => role.is_active))

  const canViewUsers = computed(() =>
    hasAccessRequirement(currentSessionState.value, { requiredPermissions: ['user.view'] }),
  )

  const canViewRoles = computed(() =>
    hasAccessRequirement(currentSessionState.value, { requiredPermissions: ['role.view'] }),
  )

  const canViewPermissions = computed(() =>
    hasAccessRequirement(currentSessionState.value, { requiredPermissions: ['permission.view'] }),
  )

  const canManageUsers = computed(() =>
    hasAccessRequirement(currentSessionState.value, { requiredPermissions: ['user.manage'] }),
  )

  const canManageRoles = computed(() =>
    hasAccessRequirement(currentSessionState.value, { requiredPermissions: ['role.manage'] }),
  )

  const availableTabs = computed<UserManagementActiveTab[]>(() => {
    const tabs: UserManagementActiveTab[] = []
    if (canViewUsers.value) tabs.push('users')
    if (canViewRoles.value) tabs.push('roles')
    if (canViewPermissions.value) tabs.push('permissions')
    return tabs.length ? tabs : ['users']
  })

  const canCreateUser = computed(() => canManageUsers.value && canViewRoles.value)

  const canCreateRole = computed(() => canManageRoles.value)

  const canAssignUserRoles = computed(() => canManageUsers.value && canViewRoles.value)

  const permissionModuleOptions = computed(() => {
    const modules = new Set(permissionItems.value.map((item) => item.module_name))
    return [...modules]
  })

  const filteredPermissionItems = computed(() => {
    const keyword = permissionFilters.keyword.trim().toLowerCase()
    return permissionItems.value.filter((item) => {
      const matchesModule = !permissionFilters.module_name || item.module_name === permissionFilters.module_name
      const matchesKeyword =
        !keyword ||
        item.name.toLowerCase().includes(keyword) ||
        item.code.toLowerCase().includes(keyword) ||
        (item.description || '').toLowerCase().includes(keyword)
      return matchesModule && matchesKeyword
    })
  })

  const {
    pageNo: permissionPageNo,
    pageSize: permissionPageSize,
    total: permissionTotal,
    pagedData: pagedPermissionItems,
    resetPagination: resetPermissionPagination,
  } = useLocalTablePagination(() => filteredPermissionItems.value)

  const totalUserPages = computed(() =>
    Math.max(1, Math.ceil(userPagination.total / Math.max(userPagination.pageSize, 1))),
  )

  const toUserStatusFilterValue = (value: AdminUserStatusFilter) => {
    if (value === 'true') return true
    if (value === 'false') return false
    return undefined
  }

  const formatDateTime = (value?: string | null) => {
    if (!value) return '-'
    return formatDateTimeFull(value)
  }

  const resetUserDialogForm = () => {
    userDialog.editingId = 0
    userDialog.form.username = ''
    userDialog.form.display_name = ''
    userDialog.form.password = ''
    userDialog.form.role_codes = []
    userDialog.form.is_active = true
  }

  const resetRoleDialogForm = () => {
    roleDialog.editingId = 0
    roleDialog.loading = false
    roleDialog.form.code = ''
    roleDialog.form.name = ''
    roleDialog.form.description = ''
    roleDialog.form.is_active = true
  }

  const loadUsers = async () => {
    usersLoading.value = true
    try {
      const data = await listAdminUsers({
        keyword: userFilters.keyword || undefined,
        role_code: userFilters.role_code || undefined,
        is_active: toUserStatusFilterValue(userFilters.is_active),
        page_no: userPagination.pageNo,
        page_size: userPagination.pageSize,
      })
      userItems.value = data.items || []
      userPagination.total = data.total || 0
    } catch (error) {
      userItems.value = []
      userPagination.total = 0
      ElMessage.error('加载用户列表失败，请稍后重试')
    } finally {
      usersLoading.value = false
    }
  }

  const loadRoles = async () => {
    rolesLoading.value = true
    try {
      const data = await listAdminRoles()
      roleOptions.value = data.items || []
    } catch (error) {
      roleOptions.value = []
      ElMessage.error('加载角色列表失败，请稍后重试')
    } finally {
      rolesLoading.value = false
    }
  }

  const loadPermissions = async () => {
    permissionsLoading.value = true
    try {
      const data = await listAdminPermissions()
      permissionItems.value = data.items || []
    } catch (error) {
      permissionItems.value = []
      ElMessage.error('加载权限列表失败，请稍后重试')
    } finally {
      permissionsLoading.value = false
    }
  }

  const loadUsersTabResources = async () => {
    const tasks: Promise<unknown>[] = []
    if (canViewUsers.value) tasks.push(loadUsers())
    if (canViewRoles.value) tasks.push(loadRoles())
    await Promise.all(tasks)
  }

  const loadRolesTabResources = async () => {
    const tasks: Promise<unknown>[] = []
    if (canViewRoles.value) tasks.push(loadRoles())
    if (canViewPermissions.value) tasks.push(loadPermissions())
    await Promise.all(tasks)
  }

  const loadPermissionsTabResources = async () => {
    if (!canViewPermissions.value) return
    await loadPermissions()
  }

  const loadActiveTabResources = async (tab: UserManagementActiveTab = activeTab.value) => {
    if (tab === 'users') {
      await loadUsersTabResources()
      return
    }
    if (tab === 'roles') {
      await loadRolesTabResources()
      return
    }
    await loadPermissionsTabResources()
  }

  const loadAccessibleManagementResources = async () => {
    const tasks: Promise<unknown>[] = []
    if (canViewUsers.value) tasks.push(loadUsers())
    if (canViewRoles.value) tasks.push(loadRoles())
    if (canViewPermissions.value) tasks.push(loadPermissions())
    await Promise.all(tasks)
  }

  const refreshCurrentTab = async () => {
    refreshingCurrentTab.value = true
    try {
      await loadActiveTabResources(activeTab.value)
    } finally {
      refreshingCurrentTab.value = false
    }
  }

  const handleTabChange = async (tabName: string | number) => {
    const nextTab = tabName as UserManagementActiveTab
    if (!availableTabs.value.includes(nextTab)) return
    activeTab.value = nextTab
    await loadActiveTabResources(nextTab)
  }

  const handleUserSearch = async () => {
    userPagination.pageNo = 1
    await loadUsers()
  }

  const resetUserFilters = async () => {
    userFilters.keyword = ''
    userFilters.role_code = ''
    userFilters.is_active = ''
    userPagination.pageNo = 1
    await loadUsers()
  }

  const handleUserPageChange = async () => {
    await loadUsers()
  }

  const handleUserPageSizeChange = async () => {
    userPagination.pageNo = 1
    await loadUsers()
  }

  const resetPermissionFilters = () => {
    permissionFilters.keyword = ''
    permissionFilters.module_name = ''
  }

  watch([() => permissionFilters.keyword, () => permissionFilters.module_name], () => {
    resetPermissionPagination()
  })

  const openCreateUserDialog = () => {
    userDialog.mode = 'create'
    resetUserDialogForm()
    userDialog.visible = true
  }

  const openEditUserDialog = (user: AdminUserItem) => {
    userDialog.mode = 'edit'
    userDialog.editingId = user.id
    userDialog.form.username = user.username
    userDialog.form.display_name = user.display_name
    userDialog.form.password = ''
    userDialog.form.role_codes = user.roles.map((role) => role.code)
    userDialog.form.is_active = user.is_active
    userDialog.visible = true
  }

  const submitUserDialog = async () => {
    if (!userDialog.form.username.trim()) {
      ElMessage.warning('请输入登录账号')
      return
    }
    if (!userDialog.form.display_name.trim()) {
      ElMessage.warning('请输入显示名称')
      return
    }
    if (userDialog.mode === 'create') {
      if (!userDialog.form.password.trim()) {
        ElMessage.warning('请输入初始密码')
        return
      }
      if (userDialog.form.password.length < 8) {
        ElMessage.warning('密码长度不能少于 8 位')
        return
      }
      if (!userDialog.form.role_codes.length) {
        ElMessage.warning('请至少选择一个角色')
        return
      }
    }

    submitting.value = true
    try {
      if (userDialog.mode === 'create') {
        await createAdminUser({
          username: userDialog.form.username.trim(),
          display_name: userDialog.form.display_name.trim(),
          password: userDialog.form.password,
          role_codes: userDialog.form.role_codes,
          is_active: userDialog.form.is_active,
        })
        ElMessage.success('用户创建成功')
      } else {
        await updateAdminUser(userDialog.editingId, {
          username: userDialog.form.username.trim(),
          display_name: userDialog.form.display_name.trim(),
        })
        ElMessage.success('用户信息已更新')
      }
      userDialog.visible = false
      await loadUsersTabResources()
    } finally {
      submitting.value = false
    }
  }

  const openUserDetail = async (user: AdminUserItem) => {
    userDetailDrawer.visible = true
    userDetailDrawer.loading = true
    userDetailDrawer.data = null
    try {
      userDetailDrawer.data = await getAdminUserDetail(user.id)
    } catch (error) {
      console.error(error)
      userDetailDrawer.visible = false
      ElMessage.error('加载用户详情失败，请稍后重试')
    } finally {
      userDetailDrawer.loading = false
    }
  }

  const openRoleAssignDialog = (user: AdminUserItem) => {
    roleAssignDialog.userId = user.id
    roleAssignDialog.userDisplayName = user.display_name || user.username
    roleAssignDialog.role_codes = user.roles.map((role) => role.code)
    roleAssignDialog.visible = true
  }

  const submitRoleAssign = async () => {
    if (!roleAssignDialog.role_codes.length) {
      ElMessage.warning('请至少选择一个角色')
      return
    }

    try {
      await confirmManagementAction({
        title: '确认更新角色',
        badge: '角色分配',
        headline: `确认更新“${roleAssignDialog.userDisplayName}”的角色分配吗？`,
        description: '更新后该用户的页面访问能力与按钮权限会按最新角色立即生效。',
        confirmButtonText: '确认更新',
      })
    } catch {
      return
    }

    submitting.value = true
    try {
      await updateAdminUserRoles(roleAssignDialog.userId, {
        role_codes: roleAssignDialog.role_codes,
      })
      ElMessage.success('角色分配已更新')
      roleAssignDialog.visible = false
      await loadUsersTabResources()
    } finally {
      submitting.value = false
    }
  }

  const openResetPasswordDialog = (user: AdminUserItem) => {
    passwordDialog.userId = user.id
    passwordDialog.userDisplayName = user.display_name || user.username
    passwordDialog.new_password = ''
    passwordDialog.visible = true
  }

  const submitResetPassword = async () => {
    if (!passwordDialog.new_password.trim()) {
      ElMessage.warning('请输入新密码')
      return
    }
    if (passwordDialog.new_password.length < 8) {
      ElMessage.warning('密码长度不能少于 8 位')
      return
    }

    try {
      await confirmManagementAction({
        title: '确认重置密码',
        badge: '密码重置',
        headline: `确认重置“${passwordDialog.userDisplayName}”的登录密码吗？`,
        description: '重置后旧密码将立即失效，请确认已通知对应用户。',
        confirmButtonText: '确认重置',
      })
    } catch {
      return
    }

    submitting.value = true
    try {
      await resetAdminUserPassword(passwordDialog.userId, {
        new_password: passwordDialog.new_password,
      })
      ElMessage.success('密码已重置')
      passwordDialog.visible = false
    } finally {
      submitting.value = false
    }
  }

  const toggleUserStatus = async (user: AdminUserItem) => {
    const nextStatus = !user.is_active
    try {
      await confirmManagementAction({
        title: nextStatus ? '确认启用用户' : '确认停用用户',
        badge: nextStatus ? '启用用户' : '停用用户',
        headline: nextStatus
          ? `确认启用用户“${user.display_name}”吗？`
          : `确认停用用户“${user.display_name}”吗？`,
        description: nextStatus
          ? '启用后该用户将重新获得登录和访问已授权页面的能力。'
          : '停用后该用户的当前会话会立即失效，后续将无法继续访问后台。',
        confirmButtonText: nextStatus ? '确认启用' : '确认停用',
      })
    } catch {
      return
    }

    try {
      await updateAdminUserStatus(user.id, { is_active: nextStatus })
      ElMessage.success(nextStatus ? '用户已启用' : '用户已停用')
      await loadUsersTabResources()
    } catch {
      // httpClient 拦截器已弹出错误提示
    }
  }

  const openCreateRoleDialog = () => {
    roleDialog.mode = 'create'
    resetRoleDialogForm()
    roleDialog.visible = true
  }

  const openEditRoleDialog = async (role: AdminRoleItem) => {
    roleDialog.mode = 'edit'
    roleDialog.editingId = role.id
    roleDialog.visible = true
    roleDialog.loading = true
    try {
      const detail = await getAdminRoleDetail(role.id)
      roleDialog.form.code = detail.code
      roleDialog.form.name = detail.name
      roleDialog.form.description = detail.description || ''
      roleDialog.form.is_active = detail.is_active
    } catch (error) {
      console.error(error)
      roleDialog.visible = false
      ElMessage.error('加载角色详情失败，请稍后重试')
    } finally {
      roleDialog.loading = false
    }
  }

  const submitRoleDialog = async () => {
    if (!roleDialog.form.name.trim()) {
      ElMessage.warning('请输入角色名称')
      return
    }
    if (roleDialog.mode === 'create' && !roleDialog.form.code.trim()) {
      ElMessage.warning('请输入角色编码')
      return
    }

    submitting.value = true
    try {
      if (roleDialog.mode === 'create') {
        await createAdminRole({
          code: roleDialog.form.code.trim(),
          name: roleDialog.form.name.trim(),
          description: roleDialog.form.description.trim() || null,
          is_active: roleDialog.form.is_active,
        })
        ElMessage.success('角色创建成功')
      } else {
        await updateAdminRole(roleDialog.editingId, {
          name: roleDialog.form.name.trim(),
          description: roleDialog.form.description.trim() || null,
        })
        ElMessage.success('角色信息已更新')
      }
      roleDialog.visible = false
      await loadAccessibleManagementResources()
    } finally {
      submitting.value = false
    }
  }

  const openRoleDetail = async (role: AdminRoleItem) => {
    roleDetailDrawer.visible = true
    roleDetailDrawer.loading = true
    roleDetailDrawer.data = null
    try {
      roleDetailDrawer.data = await getAdminRoleDetail(role.id)
    } catch (error) {
      console.error(error)
      roleDetailDrawer.visible = false
      ElMessage.error('加载角色详情失败，请稍后重试')
    } finally {
      roleDetailDrawer.loading = false
    }
  }

  const toggleRoleStatus = async (role: AdminRoleItem) => {
    const nextStatus = !role.is_active
    try {
      await confirmManagementAction({
        title: nextStatus ? '确认启用角色' : '确认停用角色',
        badge: nextStatus ? '启用角色' : '停用角色',
        headline: nextStatus
          ? `确认启用角色“${role.name}”吗？`
          : `确认停用角色“${role.name}”吗？`,
        description: nextStatus
          ? '启用后该角色可再次分配给用户，并恢复对应权限组能力。'
          : '停用后该角色将不再用于新分配，已有用户权限也会按当前后端策略收口。',
        confirmButtonText: nextStatus ? '确认启用' : '确认停用',
      })
    } catch {
      return
    }

    try {
      await updateAdminRoleStatus(role.id, { is_active: nextStatus })
      ElMessage.success(nextStatus ? '角色已启用' : '角色已停用')
      await loadAccessibleManagementResources()
    } catch {
      // httpClient 拦截器已弹出错误提示
    }
  }

  const handleDeleteRole = async (role: AdminRoleItem) => {
    try {
      await confirmManagementAction({
        title: '确认删除角色',
        badge: '删除角色',
        headline: `确认删除角色“${role.name}”吗？`,
        description: '删除后该角色将从当前列表移除，且操作不可恢复。',
        confirmButtonText: '确认删除',
      })
    } catch {
      return
    }

    try {
      await deleteAdminRole(role.id)
      ElMessage.success('角色已删除')
      await loadAccessibleManagementResources()
    } catch {
      // httpClient 拦截器已弹出错误提示
    }
  }

  watch(availableTabs, (tabs) => {
    if (!tabs.includes(activeTab.value)) {
      activeTab.value = tabs[0]
    }
  }, { immediate: true })

  onMounted(async () => {
    window.addEventListener(AUTH_CHANGED_EVENT_NAME, syncCurrentSessionState)
    await loadActiveTabResources(activeTab.value)
  })

  onUnmounted(() => {
    window.removeEventListener(AUTH_CHANGED_EVENT_NAME, syncCurrentSessionState)
  })

  return {
    activeRoleOptions,
    activeTab,
    availableTabs,
    canAssignUserRoles,
    canCreateRole,
    canCreateUser,
    canManageRoles,
    canManageUsers,
    canViewRoles,
    formatDateTime,
    handleDeleteRole,
    handleTabChange,
    handleUserPageChange,
    handleUserPageSizeChange,
    handleUserSearch,
    openCreateRoleDialog,
    openCreateUserDialog,
    openEditRoleDialog,
    openEditUserDialog,
    openResetPasswordDialog,
    openRoleAssignDialog,
    openRoleDetail,
    openUserDetail,
    pageSizeOptions,
    pagedPermissionItems,
    pagedRoleItems,
    passwordDialog,
    permissionFilters,
    permissionModuleOptions,
    permissionPageNo,
    permissionPageSize,
    permissionTotal,
    permissionsLoading,
    refreshCurrentTab,
    refreshingCurrentTab,
    resetPermissionFilters,
    resetUserFilters,
    roleAssignDialog,
    roleDetailDrawer,
    roleDialog,
    roleOptions,
    rolePageNo,
    rolePageSize,
    roleTotal,
    rolesLoading,
    submitResetPassword,
    submitRoleAssign,
    submitRoleDialog,
    submitUserDialog,
    submitting,
    toggleRoleStatus,
    toggleUserStatus,
    totalUserPages,
    userDetailDrawer,
    userDialog,
    userFilters,
    userItems,
    userPagination,
    usersLoading,
  }
}

