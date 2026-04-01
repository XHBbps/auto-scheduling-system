<template>
  <div class="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
    <el-tabs :model-value="activeTab" class="user-tabs" @tab-change="onHandleTabChange">
      <el-tab-pane v-if="availableTabs.includes('users')" label="用户管理" name="users" />
      <el-tab-pane v-if="availableTabs.includes('roles')" label="角色管理" name="roles" />
      <el-tab-pane v-if="availableTabs.includes('permissions')" label="权限目录" name="permissions" />
    </el-tabs>

    <div class="flex flex-wrap gap-3">
      <el-button :loading="refreshingCurrentTab" @click="onRefreshCurrentTab">刷新当前页</el-button>
      <el-button v-if="activeTab === 'users' && canCreateUser" type="primary" @click="onOpenCreateUserDialog">新增用户</el-button>
      <el-button v-if="activeTab === 'roles' && canCreateRole" type="primary" @click="onOpenCreateRoleDialog">新增角色</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { UserManagementActiveTab } from '../../composables/useUserManagementPage'

defineProps<{
  activeTab: UserManagementActiveTab
  availableTabs: UserManagementActiveTab[]
  canCreateRole: boolean
  canCreateUser: boolean
  refreshingCurrentTab: boolean
  onHandleTabChange: (tabName: string | number) => void | Promise<void>
  onRefreshCurrentTab: () => void | Promise<void>
  onOpenCreateRoleDialog: () => void
  onOpenCreateUserDialog: () => void
}>()
</script>
