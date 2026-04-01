<template>
  <el-dialog
    class="user-management-dialog user-management-user-dialog"
    v-model="userDialog.visible"
    :title="userDialog.mode === 'create' ? '新增用户' : '编辑用户'"
    width="560px"
    destroy-on-close
  >
    <el-form label-position="top" @submit.prevent>
      <div class="dialog-grid">
        <el-form-item label="登录账号">
          <el-input v-model.trim="userDialog.form.username" placeholder="请输入登录账号" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model.trim="userDialog.form.display_name" placeholder="请输入显示名称" />
        </el-form-item>
      </div>

      <template v-if="userDialog.mode === 'create'">
        <el-form-item label="初始密码">
          <el-input v-model="userDialog.form.password" type="password" show-password placeholder="请输入初始密码" />
        </el-form-item>

        <el-form-item label="分配角色">
          <el-checkbox-group v-model="userDialog.form.role_codes">
            <el-checkbox v-for="role in activeRoleOptions" :key="role.id" :value="role.code">
              {{ role.name }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="启用状态">
          <el-switch v-model="userDialog.form.is_active" inline-prompt active-text="启用" inactive-text="停用" />
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button @click="userDialog.visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="onSubmitUserDialog">
        {{ userDialog.mode === 'create' ? '确认创建' : '保存修改' }}
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="roleAssignDialog.visible" :title="`分配角色：${roleAssignDialog.userDisplayName || '未命名用户'}`" width="460px" destroy-on-close>
    <el-form label-position="top" @submit.prevent>
      <el-form-item label="角色列表">
        <el-checkbox-group v-model="roleAssignDialog.role_codes">
          <el-checkbox v-for="role in activeRoleOptions" :key="role.id" :value="role.code">
            {{ role.name }}
          </el-checkbox>
        </el-checkbox-group>
      </el-form-item>
      <div class="text-sm text-text-muted">
        提交前请确认角色范围，系统会以当前所选角色覆盖该用户原有角色。
      </div>
    </el-form>

    <template #footer>
      <el-button @click="roleAssignDialog.visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="onSubmitRoleAssign">确认更新</el-button>
    </template>
  </el-dialog>

  <el-dialog
    class="user-management-dialog user-management-password-dialog"
    v-model="passwordDialog.visible"
    :title="`重置密码：${passwordDialog.userDisplayName || '未命名用户'}`"
    width="420px"
    destroy-on-close
  >
    <el-form label-position="top" @submit.prevent>
      <el-form-item label="新密码">
        <el-input v-model="passwordDialog.new_password" type="password" show-password placeholder="请输入新密码" />
      </el-form-item>
      <div class="text-sm text-text-muted">
        提交后将立即覆盖该用户现有登录密码，请确认后再执行。
      </div>
    </el-form>

    <template #footer>
      <el-button @click="passwordDialog.visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="onSubmitResetPassword">确认重置</el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="roleDialog.visible"
    :title="roleDialog.mode === 'create' ? '新增角色' : '编辑角色'"
    width="560px"
    destroy-on-close
    v-loading="roleDialog.loading"
  >
    <el-form label-position="top" @submit.prevent>
      <div class="dialog-grid">
        <el-form-item label="角色编码">
          <el-input v-model.trim="roleDialog.form.code" :disabled="roleDialog.mode === 'edit'" placeholder="例如 planner.manager" />
        </el-form-item>
        <el-form-item label="角色名称">
          <el-input v-model.trim="roleDialog.form.name" placeholder="请输入角色中文名称" />
        </el-form-item>
      </div>

      <el-form-item label="角色说明">
        <el-input v-model.trim="roleDialog.form.description" type="textarea" :rows="3" placeholder="请输入角色说明" />
      </el-form-item>

      <el-form-item v-if="roleDialog.mode === 'create'" label="启用状态">
        <el-switch v-model="roleDialog.form.is_active" inline-prompt active-text="启用" inactive-text="停用" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="roleDialog.visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="onSubmitRoleDialog">
        {{ roleDialog.mode === 'create' ? '确认创建' : '保存修改' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import type { AdminRoleItem } from '../../types/apiModels'
import type {
  PasswordDialogState,
  RoleAssignDialogState,
  RoleDialogState,
  UserDialogState,
} from '../../composables/useUserManagementPage'

const userDialog = defineModel<UserDialogState>('userDialog', { required: true })
const roleAssignDialog = defineModel<RoleAssignDialogState>('roleAssignDialog', { required: true })
const passwordDialog = defineModel<PasswordDialogState>('passwordDialog', { required: true })
const roleDialog = defineModel<RoleDialogState>('roleDialog', { required: true })

defineProps<{
  activeRoleOptions: AdminRoleItem[]
  submitting: boolean
  onSubmitResetPassword: () => void | Promise<void>
  onSubmitRoleAssign: () => void | Promise<void>
  onSubmitRoleDialog: () => void | Promise<void>
  onSubmitUserDialog: () => void | Promise<void>
}>()
</script>
