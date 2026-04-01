<template>
  <div class="space-y-5">
    <div class="panel-block">
      <div class="mb-4 flex items-center justify-between">
        <div class="panel-title">角色列表</div>
        <div class="text-xs text-text-muted">系统内置角色不可停用、不可删除；仍有用户绑定的角色不可删除。</div>
      </div>

      <el-table v-loading="rolesLoading" :data="pagedRoleItems" class="app-data-table" empty-text="暂无角色数据">
        <el-table-column prop="name" label="角色名称" min-width="140" />
        <el-table-column prop="code" label="角色编码" min-width="150" />
        <el-table-column prop="description" label="角色说明" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getActiveStatusBadgeMeta(row.is_active)" />
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110" align="center">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getSystemBuiltInBadgeMeta(row.is_system)" />
          </template>
        </el-table-column>
        <el-table-column prop="assigned_user_count" label="绑定用户" width="100" align="center" />
        <el-table-column prop="permission_count" label="权限数" width="90" align="center" />
        <el-table-column label="最近更新" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="360" fixed="right">
          <template #default="{ row }">
            <div class="flex flex-wrap justify-end gap-2">
              <el-button size="small" @click="onOpenRoleDetail(row)">详情</el-button>

              <template v-if="canManageRoles">
                <el-button size="small" @click="onOpenEditRoleDialog(row)">编辑</el-button>

                <el-tooltip
                  :disabled="!row.is_system"
                  content="系统内置角色不可停用，请保留为启用状态。"
                  placement="top"
                >
                  <span class="inline-flex">
                    <el-button
                      size="small"
                      :type="row.is_active ? 'warning' : 'success'"
                      plain
                      :disabled="row.is_system"
                      @click="onToggleRoleStatus(row)"
                    >
                      {{ row.is_active ? '停用' : '启用' }}
                    </el-button>
                  </span>
                </el-tooltip>

                <el-tooltip
                  :disabled="!row.is_system && row.assigned_user_count === 0"
                  :content="row.is_system ? '系统内置角色不可删除。' : '当前角色仍有用户绑定，无法删除。'"
                  placement="top"
                >
                  <span class="inline-flex">
                    <el-button
                      size="small"
                      type="danger"
                      plain
                      :disabled="row.is_system || row.assigned_user_count > 0"
                      @click="onHandleDeleteRole(row)"
                    >
                      删除
                    </el-button>
                  </span>
                </el-tooltip>
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="mt-5 flex justify-end">
        <el-pagination
          v-model:current-page="rolePageNo"
          v-model:page-size="rolePageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :total="roleTotal"
          :page-sizes="pageSizeOptions"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppStatusBadge from '../AppStatusBadge.vue'
import type { AdminRoleItem } from '../../types/apiModels'
import { getActiveStatusBadgeMeta, getSystemBuiltInBadgeMeta } from '../../utils/statusPresentation'

const rolePageNo = defineModel<number>('rolePageNo', { required: true })
const rolePageSize = defineModel<number>('rolePageSize', { required: true })

defineProps<{
  canManageRoles: boolean
  pageSizeOptions: readonly number[]
  pagedRoleItems: AdminRoleItem[]
  roleTotal: number
  rolesLoading: boolean
  formatDateTime: (value?: string | null) => string | null
  onHandleDeleteRole: (role: AdminRoleItem) => void | Promise<void>
  onOpenEditRoleDialog: (role: AdminRoleItem) => void | Promise<void>
  onOpenRoleDetail: (role: AdminRoleItem) => void | Promise<void>
  onToggleRoleStatus: (role: AdminRoleItem) => void | Promise<void>
}>()
</script>
