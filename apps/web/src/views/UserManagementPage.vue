<template>
  <div class="space-y-6">
    <div class="tech-card rounded-3xl p-6">
      <UserManagementHeader
        :active-tab="activeTab"
        :available-tabs="availableTabs"
        :can-create-role="canCreateRole"
        :can-create-user="canCreateUser"
        :refreshing-current-tab="refreshingCurrentTab"
        :on-handle-tab-change="handleTabChange"
        :on-refresh-current-tab="refreshCurrentTab"
        :on-open-create-role-dialog="openCreateRoleDialog"
        :on-open-create-user-dialog="openCreateUserDialog"
      />

      <UserListSection
        v-show="activeTab === 'users'"
        v-model:user-filters="userFilters"
        v-model:user-pagination="userPagination"
        :can-assign-user-roles="canAssignUserRoles"
        :can-manage-users="canManageUsers"
        :can-view-roles="canViewRoles"
        :page-size-options="pageSizeOptions"
        :role-options="roleOptions"
        :total-user-pages="totalUserPages"
        :user-items="userItems"
        :users-loading="usersLoading"
        :format-date-time="formatDateTime"
        :on-handle-user-page-change="handleUserPageChange"
        :on-handle-user-page-size-change="handleUserPageSizeChange"
        :on-handle-user-search="handleUserSearch"
        :on-open-edit-user-dialog="openEditUserDialog"
        :on-open-reset-password-dialog="openResetPasswordDialog"
        :on-open-role-assign-dialog="openRoleAssignDialog"
        :on-open-user-detail="openUserDetail"
        :on-reset-user-filters="resetUserFilters"
        :on-toggle-user-status="toggleUserStatus"
      />

      <RoleListSection
        v-show="activeTab === 'roles'"
        v-model:role-page-no="rolePageNo"
        v-model:role-page-size="rolePageSize"
        :can-manage-roles="canManageRoles"
        :page-size-options="pageSizeOptions"
        :paged-role-items="pagedRoleItems"
        :role-total="roleTotal"
        :roles-loading="rolesLoading"
        :format-date-time="formatDateTime"
        :on-handle-delete-role="handleDeleteRole"
        :on-open-edit-role-dialog="openEditRoleDialog"
        :on-open-role-detail="openRoleDetail"
        :on-toggle-role-status="toggleRoleStatus"
      />

      <PermissionListSection
        v-show="activeTab === 'permissions'"
        v-model:permission-filters="permissionFilters"
        v-model:permission-page-no="permissionPageNo"
        v-model:permission-page-size="permissionPageSize"
        :page-size-options="pageSizeOptions"
        :paged-permission-items="pagedPermissionItems"
        :permission-module-options="permissionModuleOptions"
        :permission-total="permissionTotal"
        :permissions-loading="permissionsLoading"
        :on-reset-permission-filters="resetPermissionFilters"
      />
    </div>

    <UserManagementDialogs
      v-model:user-dialog="userDialog"
      v-model:role-assign-dialog="roleAssignDialog"
      v-model:password-dialog="passwordDialog"
      v-model:role-dialog="roleDialog"
      :active-role-options="activeRoleOptions"
      :submitting="submitting"
      :on-submit-reset-password="submitResetPassword"
      :on-submit-role-assign="submitRoleAssign"
      :on-submit-role-dialog="submitRoleDialog"
      :on-submit-user-dialog="submitUserDialog"
    />

    <UserManagementDrawers
      v-model:user-detail-drawer="userDetailDrawer"
      v-model:role-detail-drawer="roleDetailDrawer"
      :format-date-time="formatDateTime"
    />
  </div>
</template>

<script setup lang="ts">
import UserManagementDialogs from '../components/user-management/UserManagementDialogs.vue'
import UserManagementDrawers from '../components/user-management/UserManagementDrawers.vue'
import UserManagementHeader from '../components/user-management/UserManagementHeader.vue'
import UserListSection from '../components/user-management/UserListSection.vue'
import PermissionListSection from '../components/user-management/PermissionListSection.vue'
import RoleListSection from '../components/user-management/RoleListSection.vue'
import { useUserManagementPage } from '../composables/useUserManagementPage'
import '../components/user-management/userManagement.css'

const {
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
} = useUserManagementPage()
</script>
