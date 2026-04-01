import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/httpClient'
import type { AuthSessionInfo } from '../types/apiModels'
import {
  AUTH_CHANGED_EVENT_NAME,
  ensureAuthSession,
  formatAuthSessionExpiresAtDisplay,
  getAuthSessionState,
  normalizeAuthRedirectPath,
  saveAuthSession,
} from '../utils/authSession'

export const useAdminAccess = () => {
  const route = useRoute()
  const router = useRouter()

  const currentSessionState = ref(getAuthSessionState())
  const username = ref(currentSessionState.value.user?.username || '')
  const password = ref('')
  const loading = ref(false)

  const syncCurrentSessionState = () => {
    currentSessionState.value = getAuthSessionState()
    if (!username.value.trim() && currentSessionState.value.user?.username) {
      username.value = currentSessionState.value.user.username
    }
  }

  const activeSessionSummary = computed(() => {
    if (!currentSessionState.value.authenticated || !currentSessionState.value.user) {
      return ''
    }
    const expiresLabel = formatAuthSessionExpiresAtDisplay(currentSessionState.value.expiresAt)
    return expiresLabel
      ? `当前已登录用户：${currentSessionState.value.user.display_name}，会话有效期至 ${expiresLabel}`
      : `当前已登录用户：${currentSessionState.value.user.display_name}`
  })

  const redirectPath = computed(() => {
    return normalizeAuthRedirectPath(route.query.redirect)
  })

  const redirectIfAuthenticated = async () => {
    const passed = await ensureAuthSession()
    syncCurrentSessionState()
    if (!passed) {
      return
    }
    await router.replace(redirectPath.value)
  }

  const handleSubmit = async () => {
    const normalizedUsername = username.value.trim()
    const normalizedPassword = password.value

    if (!normalizedUsername) {
      ElMessage.warning('请输入登录账号')
      return
    }
    if (!normalizedPassword) {
      ElMessage.warning('请输入登录密码')
      return
    }

    loading.value = true
    try {
      const sessionInfo = await request.post<AuthSessionInfo>('/api/auth/login', {
        username: normalizedUsername,
        password: normalizedPassword,
      })
      saveAuthSession(sessionInfo)
      syncCurrentSessionState()
      const expiresLabel = formatAuthSessionExpiresAtDisplay(sessionInfo.expires_at)
      ElMessage.success(expiresLabel ? `登录成功，会话有效期至 ${expiresLabel}` : '登录成功')
      password.value = ''
      await router.replace(redirectPath.value)
    } catch {
      password.value = ''
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    window.addEventListener(AUTH_CHANGED_EVENT_NAME, syncCurrentSessionState)
    void redirectIfAuthenticated()
  })

  onUnmounted(() => {
    window.removeEventListener(AUTH_CHANGED_EVENT_NAME, syncCurrentSessionState)
  })

  return {
    activeSessionSummary,
    handleSubmit,
    loading,
    password,
    username,
  }
}
