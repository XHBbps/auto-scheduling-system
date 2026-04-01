<template>
  <el-drawer v-model="userDetailDrawer.visible" title="用户详情" size="460px" destroy-on-close v-loading="userDetailDrawer.loading">
    <template v-if="userDetailDrawer.data">
      <div class="detail-stack">
        <div class="detail-card">
          <div class="detail-card__title">{{ userDetailDrawer.data.display_name }}</div>
          <div class="detail-card__desc">{{ userDetailDrawer.data.username }}</div>
          <div class="mt-4 flex flex-wrap gap-2">
            <AppStatusBadge v-bind="getUserAccountStatusBadgeMeta(userDetailDrawer.data.is_active)" />
            <el-tag
              v-for="role in userDetailDrawer.data.roles"
              :key="role.code"
              effect="dark"
              class="!border-none !bg-brand/15 !text-brand"
            >
              {{ role.name }}
            </el-tag>
          </div>
        </div>

        <div class="detail-grid">
          <div class="detail-item">
            <div class="detail-item__label">最近登录</div>
            <div class="detail-item__value">{{ formatDateTime(userDetailDrawer.data.last_login_at) || '-' }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-item__label">创建时间</div>
            <div class="detail-item__value">{{ formatDateTime(userDetailDrawer.data.created_at) || '-' }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-item__label">最近更新</div>
            <div class="detail-item__value">{{ formatDateTime(userDetailDrawer.data.updated_at) || '-' }}</div>
          </div>
        </div>
      </div>
    </template>
    <div v-else-if="!userDetailDrawer.loading" class="text-sm text-text-muted">暂无用户详情数据。</div>
  </el-drawer>

  <el-drawer v-model="roleDetailDrawer.visible" title="角色详情" size="520px" destroy-on-close v-loading="roleDetailDrawer.loading">
    <template v-if="roleDetailDrawer.data">
      <div class="detail-stack">
        <div class="detail-card">
          <div class="detail-card__title">{{ roleDetailDrawer.data.name }}</div>
          <div class="detail-card__desc">{{ roleDetailDrawer.data.code }}</div>
          <div class="mt-4 flex flex-wrap gap-2">
            <AppStatusBadge v-bind="getRoleStatusBadgeMeta(roleDetailDrawer.data.is_active)" />
            <AppStatusBadge v-bind="getSystemBuiltInBadgeMeta(roleDetailDrawer.data.is_system)" />
          </div>
          <div class="mt-4 text-sm leading-6 text-text-muted">
            {{ roleDetailDrawer.data.description || '暂无角色说明。' }}
          </div>
        </div>

        <div class="detail-grid">
          <div class="detail-item">
            <div class="detail-item__label">绑定用户</div>
            <div class="detail-item__value">{{ roleDetailDrawer.data.assigned_user_count }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-item__label">权限数</div>
            <div class="detail-item__value">{{ roleDetailDrawer.data.permission_count }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-item__label">最近更新</div>
            <div class="detail-item__value">{{ formatDateTime(roleDetailDrawer.data.updated_at) || '-' }}</div>
          </div>
        </div>

        <div class="panel-block !p-4">
          <div class="panel-title mb-3">权限列表</div>
          <div v-if="roleDetailDrawer.data.permissions.length" class="flex flex-wrap gap-2">
            <el-tag
              v-for="permission in roleDetailDrawer.data.permissions"
              :key="permission.code"
              effect="dark"
              class="!border-none !bg-brand/15 !text-brand"
            >
              {{ permission.name }}
            </el-tag>
          </div>
          <div v-else class="text-sm text-text-muted">当前角色暂未绑定权限。</div>
        </div>
      </div>
    </template>
    <div v-else-if="!roleDetailDrawer.loading" class="text-sm text-text-muted">暂无角色详情数据。</div>
  </el-drawer>
</template>

<script setup lang="ts">
import AppStatusBadge from '../AppStatusBadge.vue'
import type { RoleDetailDrawerState, UserDetailDrawerState } from '../../composables/useUserManagementPage'
import { getActiveStatusBadgeMeta, getSystemBuiltInBadgeMeta } from '../../utils/statusPresentation'

const userDetailDrawer = defineModel<UserDetailDrawerState>('userDetailDrawer', { required: true })
const roleDetailDrawer = defineModel<RoleDetailDrawerState>('roleDetailDrawer', { required: true })

defineProps<{
  formatDateTime: (value?: string | null) => string | null
}>()

const getUserAccountStatusBadgeMeta = (value?: boolean | null) => ({
  ...getActiveStatusBadgeMeta(value),
  label: value ? '账号已启用' : '账号已停用',
})

const getRoleStatusBadgeMeta = (value?: boolean | null) => ({
  ...getActiveStatusBadgeMeta(value),
  label: value ? '角色已启用' : '角色已停用',
})
</script>
