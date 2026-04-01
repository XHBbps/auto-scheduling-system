<template>
  <section class="login-panel">
    <div class="login-panel__card">
      <div class="login-panel__chrome" aria-hidden="true">
        <span class="login-panel__chrome-dot login-panel__chrome-dot--active"></span>
        <span class="login-panel__chrome-dot"></span>
        <span class="login-panel__chrome-dot"></span>
      </div>

      <div v-if="props.activeSessionSummary" class="login-session-banner">
        <span class="login-session-banner__label">当前会话</span>
        <span>{{ props.activeSessionSummary }}</span>
      </div>

      <el-form class="login-form" label-position="top" @submit.prevent>
        <el-form-item label="登录账号">
          <el-input
            :model-value="props.username"
            class="login-input"
            placeholder="请输入登录账号"
            autocomplete="username"
            @update:model-value="updateUsername"
            @keyup.enter="emitSubmit"
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="登录密码">
          <el-input
            :model-value="props.password"
            class="login-input"
            type="password"
            show-password
            placeholder="请输入登录密码"
            autocomplete="current-password"
            @update:model-value="updatePassword"
            @keyup.enter="emitSubmit"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <div class="login-form__actions">
          <el-button class="login-form__primary" type="primary" :loading="props.loading" @click="emitSubmit">
            <span>验证并进入</span>
            <el-icon><Right /></el-icon>
          </el-button>
        </div>
      </el-form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Lock, Right, User } from '@element-plus/icons-vue'

const props = defineProps<{
  username: string
  password: string
  loading: boolean
  activeSessionSummary: string
}>()

const emit = defineEmits<{
  'update:username': [value: string]
  'update:password': [value: string]
  submit: []
}>()

const updateUsername = (value: string | number | undefined) => {
  emit('update:username', String(value ?? ''))
}

const updatePassword = (value: string | number | undefined) => {
  emit('update:password', String(value ?? ''))
}

const emitSubmit = () => {
  emit('submit')
}
</script>

<style scoped>
.login-panel {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.login-panel__card {
  position: relative;
  width: min(100%, 408px);
  padding: 22px 22px 24px;
  border-radius: 28px;
  background: linear-gradient(180deg, #111715 0%, #0d1210 100%);
  border: 1px solid rgba(119, 144, 126, 0.18);
  box-shadow:
    0 24px 56px rgba(0, 0, 0, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.login-panel__card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent 14%);
  pointer-events: none;
}

.login-panel__chrome {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.login-panel__chrome-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: rgba(160, 171, 164, 0.2);
}

.login-panel__chrome-dot--active {
  background: #82d695;
  box-shadow: 0 0 8px rgba(130, 214, 149, 0.28);
}

.login-session-banner {
  margin-top: 18px;
  padding: 13px 14px;
  display: grid;
  gap: 6px;
  border-radius: 16px;
  background: #151d19;
  border: 1px solid rgba(122, 223, 139, 0.1);
  color: #e3f6e7;
  font-size: 12px;
  line-height: 1.7;
}

.login-session-banner__label {
  color: #9cf0ac;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.login-form {
  margin-top: 20px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.login-form :deep(.el-form-item__label) {
  margin-bottom: 10px;
  color: rgba(243, 247, 244, 0.78);
  font-size: 13px;
  letter-spacing: 0.01em;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 54px;
  border-radius: 16px;
  box-shadow: none !important;
  background: #171f1b;
  border: 1px solid rgba(120, 138, 126, 0.18);
  padding: 0 16px 0 14px;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  background: #19231e;
  border-color: rgba(135, 157, 143, 0.24);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  background: #19231d;
  border-color: rgba(122, 223, 139, 0.32);
  box-shadow: 0 0 0 4px rgba(122, 223, 139, 0.04) !important;
}

.login-form :deep(.el-input__inner) {
  color: #ffffff;
  font-size: 14px;
  caret-color: #ffffff;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: rgba(215, 225, 218, 0.32);
}

.login-form :deep(.el-input__inner:-webkit-autofill),
.login-form :deep(.el-input__inner:-webkit-autofill:hover),
.login-form :deep(.el-input__inner:-webkit-autofill:focus),
.login-form :deep(.el-textarea__inner:-webkit-autofill),
.login-form :deep(.el-textarea__inner:-webkit-autofill:hover),
.login-form :deep(.el-textarea__inner:-webkit-autofill:focus) {
  -webkit-text-fill-color: #ffffff !important;
  caret-color: #ffffff;
  box-shadow: 0 0 0 1000px #171f1b inset !important;
  transition: background-color 99999s ease-in-out 0s;
}

.login-form :deep(.el-input__prefix) {
  color: rgba(156, 238, 171, 0.62);
  margin-right: 8px;
}

.login-form__actions {
  margin-top: 24px;
}

.login-form__primary {
  width: 100%;
  height: 54px;
  border: none;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #0c130d !important;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.02em;
  background: linear-gradient(135deg, #92f3a5 0%, #74de89 100%) !important;
  box-shadow:
    0 14px 28px rgba(113, 221, 135, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.26);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    filter 0.2s ease;
}

.login-form__primary:hover {
  transform: translateY(-1px);
  filter: saturate(1.02);
  box-shadow:
    0 16px 32px rgba(113, 221, 135, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

@media (max-width: 1220px) {
  .login-panel {
    justify-content: center;
  }

  .login-panel__card {
    width: 100%;
    max-width: 440px;
  }
}

@media (max-width: 720px) {
  .login-panel__card {
    padding: 18px 18px 20px;
    border-radius: 22px;
  }
}
</style>
