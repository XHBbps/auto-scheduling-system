<template>
  <div class="space-y-5">
    <div class="panel-block">
      <div class="mb-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div class="panel-title">权限目录</div>
          <div class="mt-1 text-sm text-text-muted">用于查看系统内置权限清单，便于后续角色体系扩展与校验。</div>
        </div>

        <div class="grid gap-3 lg:grid-cols-[220px_220px_auto]">
          <el-input v-model.trim="permissionFilters.keyword" placeholder="按权限名称 / 编码搜索" clearable />
          <el-select v-model="permissionFilters.module_name" placeholder="筛选模块" clearable>
            <el-option
              v-for="moduleName in permissionModuleOptions"
              :key="moduleName"
              :label="moduleName"
              :value="moduleName"
            />
          </el-select>
          <el-button @click="onResetPermissionFilters">重置</el-button>
        </div>
      </div>

      <el-table
        v-loading="permissionsLoading"
        :data="pagedPermissionItems"
        class="app-data-table"
        empty-text="暂无权限目录数据"
      >
        <el-table-column prop="module_name" label="所属模块" min-width="140" />
        <el-table-column prop="name" label="权限名称" min-width="160" />
        <el-table-column prop="code" label="权限编码" min-width="180" />
        <el-table-column prop="description" label="权限说明" min-width="240" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getActiveStatusBadgeMeta(row.is_active)" />
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getSystemBuiltInBadgeMeta(row.is_system)" />
          </template>
        </el-table-column>
      </el-table>

      <div class="mt-5 flex justify-end">
        <el-pagination
          v-model:current-page="permissionPageNo"
          v-model:page-size="permissionPageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :total="permissionTotal"
          :page-sizes="pageSizeOptions"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppStatusBadge from '../AppStatusBadge.vue'
import type { AdminPermissionItem } from '../../types/apiModels'
import type { PermissionFiltersState } from '../../composables/useUserManagementPage'
import { getActiveStatusBadgeMeta, getSystemBuiltInBadgeMeta } from '../../utils/statusPresentation'

const permissionFilters = defineModel<PermissionFiltersState>('permissionFilters', { required: true })
const permissionPageNo = defineModel<number>('permissionPageNo', { required: true })
const permissionPageSize = defineModel<number>('permissionPageSize', { required: true })

defineProps<{
  pageSizeOptions: readonly number[]
  pagedPermissionItems: AdminPermissionItem[]
  permissionModuleOptions: string[]
  permissionTotal: number
  permissionsLoading: boolean
  onResetPermissionFilters: () => void
}>()
</script>
