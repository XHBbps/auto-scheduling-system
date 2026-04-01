<template>
  <div class="space-y-5">
    <div class="panel-block">
      <div class="mb-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div class="panel-title">系统用户</div>
          <div class="mt-1 text-sm text-text-muted">
            共 {{ userPagination.total }} 位用户，当前第 {{ userPagination.pageNo }} / {{ totalUserPages }} 页
          </div>
        </div>

        <div class="flex flex-wrap gap-3">
          <el-input
            v-model.trim="userFilters.keyword"
            placeholder="按登录账号 / 显示名称搜索"
            clearable
            class="!w-[220px]"
            @keyup.enter="onHandleUserSearch"
          />
          <el-select v-if="canViewRoles" v-model="userFilters.role_code" placeholder="筛选角色" clearable class="!w-[220px]">
            <el-option v-for="role in roleOptions" :key="role.id" :label="role.name" :value="role.code" />
          </el-select>
          <el-select v-model="userFilters.is_active" placeholder="启用状态" clearable class="!w-[220px]">
            <el-option label="已启用" value="true" />
            <el-option label="已停用" value="false" />
          </el-select>
          <el-button type="primary" @click="onHandleUserSearch">搜索</el-button>
          <el-button @click="onResetUserFilters">重置</el-button>
        </div>
      </div>

      <el-table v-loading="usersLoading" :data="userItems" class="app-data-table" empty-text="暂无用户数据">
        <el-table-column prop="username" label="登录账号" min-width="140" />
        <el-table-column prop="display_name" label="显示名称" min-width="150" />
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <div class="flex flex-wrap gap-2">
              <el-tag
                v-for="role in row.roles"
                :key="`${row.id}-${role.code}`"
                effect="dark"
                class="!border-none !bg-brand/15 !text-brand"
              >
                {{ role.name }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getActiveStatusBadgeMeta(row.is_active)" />
          </template>
        </el-table-column>
        <el-table-column label="最近登录" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.last_login_at) || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="最近更新" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="440" fixed="right">
          <template #default="{ row }">
            <div class="user-action-strip">
              <el-button size="small" @click="onOpenUserDetail(row)">详情</el-button>
              <template v-if="canManageUsers">
                <el-button size="small" @click="onOpenEditUserDialog(row)">编辑</el-button>
                <el-button v-if="canAssignUserRoles" size="small" @click="onOpenRoleAssignDialog(row)">分配角色</el-button>
                <el-button size="small" @click="onOpenResetPasswordDialog(row)">重置密码</el-button>
                <el-button size="small" :type="row.is_active ? 'warning' : 'success'" plain @click="onToggleUserStatus(row)">
                  {{ row.is_active ? '停用' : '启用' }}
                </el-button>
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="mt-5 flex justify-end">
        <el-pagination
          v-model:current-page="userPagination.pageNo"
          v-model:page-size="userPagination.pageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :total="userPagination.total"
          :page-sizes="pageSizeOptions"
          @current-change="onHandleUserPageChange"
          @size-change="onHandleUserPageSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppStatusBadge from '../AppStatusBadge.vue'
import type { AdminRoleItem, AdminUserItem } from '../../types/apiModels'
import type { UserFiltersState, UserPaginationState } from '../../composables/useUserManagementPage'
import { getActiveStatusBadgeMeta } from '../../utils/statusPresentation'

const userFilters = defineModel<UserFiltersState>('userFilters', { required: true })
const userPagination = defineModel<UserPaginationState>('userPagination', { required: true })

defineProps<{
  canAssignUserRoles: boolean
  canManageUsers: boolean
  canViewRoles: boolean
  pageSizeOptions: readonly number[]
  roleOptions: AdminRoleItem[]
  totalUserPages: number
  userItems: AdminUserItem[]
  usersLoading: boolean
  formatDateTime: (value?: string | null) => string | null
  onHandleUserPageChange: () => void | Promise<void>
  onHandleUserPageSizeChange: () => void | Promise<void>
  onHandleUserSearch: () => void | Promise<void>
  onOpenEditUserDialog: (user: AdminUserItem) => void
  onOpenResetPasswordDialog: (user: AdminUserItem) => void
  onOpenRoleAssignDialog: (user: AdminUserItem) => void
  onOpenUserDetail: (user: AdminUserItem) => void | Promise<void>
  onResetUserFilters: () => void | Promise<void>
  onToggleUserStatus: (user: AdminUserItem) => void | Promise<void>
}>()
</script>
