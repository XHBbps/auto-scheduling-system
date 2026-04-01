<template>
  <el-container class="h-screen w-full bg-surface-page">
    <el-aside :width="isCollapse ? '80px' : '240px'" class="tech-sidebar transition-all duration-300 flex flex-col">
      <div class="h-20 flex items-center px-6 text-white font-bold text-xl overflow-hidden whitespace-nowrap border-b border-border/80">
        <template v-if="isCollapse">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="brandMarkFillCollapsed" x1="8" y1="5" x2="31" y2="35" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#9AF1A8" />
                  <stop offset="1" stop-color="#78D789" />
                </linearGradient>
              </defs>
              <rect x="4.5" y="4.5" width="31" height="31" rx="8.6" fill="url(#brandMarkFillCollapsed)" />
              <rect x="10.2" y="10.1" width="8.2" height="8.2" rx="2.6" fill="#152219" />
              <rect x="21.6" y="10.1" width="8.2" height="8.2" rx="2.6" fill="#72BC80" />
              <rect x="10.2" y="21.5" width="8.2" height="8.2" rx="2.6" fill="#72BC80" />
              <rect x="21.6" y="21.5" width="8.2" height="8.2" rx="2.6" fill="#152219" />
            </svg>
          </span>
        </template>
        <div v-else class="flex items-center gap-3">
          <div class="brand-badge">
            <span class="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="brandMarkFillExpanded" x1="8" y1="5" x2="31" y2="35" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#9AF1A8" />
                    <stop offset="1" stop-color="#78D789" />
                  </linearGradient>
                </defs>
                <rect x="4.5" y="4.5" width="31" height="31" rx="8.6" fill="url(#brandMarkFillExpanded)" />
                <rect x="10.2" y="10.1" width="8.2" height="8.2" rx="2.6" fill="#152219" />
                <rect x="21.6" y="10.1" width="8.2" height="8.2" rx="2.6" fill="#72BC80" />
                <rect x="10.2" y="21.5" width="8.2" height="8.2" rx="2.6" fill="#72BC80" />
                <rect x="21.6" y="21.5" width="8.2" height="8.2" rx="2.6" fill="#152219" />
              </svg>
            </span>
          </div>
          <span class="brand-title">AutoSchedule</span>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto px-4 py-2 custom-scrollbar">
        <div v-if="!isCollapse" class="menu-section mt-4">MENU</div>
        <el-menu
          :default-active="activeMenu"
          class="border-none bg-transparent"
          text-color="#a0aab2"
          active-text-color="#82d695"
          :collapse="isCollapse"
          router
        >
          <el-menu-item v-if="canAccessDashboard" index="/dashboard" class="menu-item">
            <el-icon><DataBoard /></el-icon>
            <span>排产总览</span>
          </el-menu-item>
          <el-menu-item v-if="canAccessWorkCalendar" index="/admin/work-calendar" class="menu-item">
            <el-icon><Calendar /></el-icon>
            <span>排产日历</span>
          </el-menu-item>
          <el-menu-item v-if="canAccessScheduleList" index="/schedules" class="menu-item">
            <el-icon><List /></el-icon>
            <span>排产列表</span>
          </el-menu-item>
          <el-menu-item v-if="canAccessPartScheduleList" index="/part-schedules" class="menu-item">
            <el-icon><Tickets /></el-icon>
            <span>零件排产</span>
          </el-menu-item>
          <template v-if="showManagementMenus">
            <div v-if="!isCollapse" class="menu-section mt-6">SETTINGS</div>
            <el-sub-menu v-if="showBaseParamMenu" index="/admin/base-params" class="menu-item">
              <template #title>
                <el-icon><Setting /></el-icon>
                <span>基础参数</span>
              </template>
              <el-menu-item v-if="canAccessAssemblyTime" index="/admin/assembly-times" class="sub-menu-item">装配时长配置</el-menu-item>
              <el-menu-item v-if="canAccessMachineCycle" index="/admin/machine-cycle" class="sub-menu-item">整机周期基准</el-menu-item>
              <el-menu-item v-if="canAccessPartCycle" index="/admin/part-cycle" class="sub-menu-item">零件周期基准</el-menu-item>
            </el-sub-menu>
            <el-sub-menu v-if="showSyncMenu" index="/admin/sync-config" class="menu-item">
              <template #title>
                <el-icon><Refresh /></el-icon>
                <span>同步配置</span>
              </template>
              <el-menu-item v-if="canAccessSyncConsole" index="/admin/sync" class="sub-menu-item">数据同步</el-menu-item>
              <el-menu-item v-if="canAccessSyncLogList" index="/sync-logs" class="sub-menu-item">同步日志</el-menu-item>
            </el-sub-menu>
            <el-sub-menu v-if="showSystemMenu" index="/admin/system-management" class="menu-item">
              <template #title>
                <el-icon><User /></el-icon>
                <span>系统管理</span>
              </template>
              <el-menu-item v-if="canAccessUserManagement" index="/admin/users" class="sub-menu-item">用户管理</el-menu-item>
              <el-menu-item v-if="canAccessIssueList" index="/issues" class="sub-menu-item">异常管理</el-menu-item>
            </el-sub-menu>
          </template>

          <div v-if="!isCollapse && showDataMenu" class="menu-section mt-6">DATA</div>
          <el-sub-menu v-if="showDataMenu" index="/data" class="menu-item">
            <template #title>
              <el-icon><Coin /></el-icon>
              <span>外源数据</span>
            </template>
            <el-menu-item v-if="canAccessSalesPlanData" index="/data/sales-plan" class="sub-menu-item">销售计划表</el-menu-item>
            <el-menu-item v-if="canAccessBomData" index="/data/bom" class="sub-menu-item">BOM 物料清单</el-menu-item>
            <el-menu-item v-if="canAccessProductionOrderData" index="/data/production-orders" class="sub-menu-item">生产订单历史</el-menu-item>
            <el-menu-item v-if="canAccessMachineCycleHistoryData" index="/data/machine-cycle-history" class="sub-menu-item">整机周期历史</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </div>

      <div v-if="!isCollapse" class="p-4 mt-auto">
        <div class="quick-entry-card">
          <div class="quick-entry-card__icon">
            <el-icon :size="18"><Cpu /></el-icon>
          </div>
          <div class="quick-entry-card__title">排产引擎</div>
          <div class="quick-entry-card__desc">智能优化生产计划</div>
          <el-button class="w-full !rounded-xl" type="primary" :loading="scheduleRunning" @click="handleRunSchedule">
            {{ scheduleRunning ? '排产中...' : canRunSchedule ? '一键排产' : authenticated ? '无排产权限' : '前往登录' }}
          </el-button>
        </div>
      </div>
    </el-aside>

    <el-container class="flex flex-col relative bg-surface-page">
      <el-header class="h-20 flex items-center justify-between px-8 z-10 glass-header">
        <div class="flex items-center gap-6">
          <el-button
            class="header-toggle"
            @click="isCollapse = !isCollapse"
          >
            <el-icon :size="18">
              <Fold v-if="!isCollapse" />
              <Expand v-else />
            </el-icon>
          </el-button>
          <div class="text-xl font-semibold text-white">{{ route.meta.title || 'Dashboard' }}</div>
        </div>

        <div class="flex items-center gap-3">
          <el-tag
            size="small"
            effect="dark"
            :class="authenticated ? '!border-none !bg-brand/20 !text-brand' : '!border-none !bg-status-warning/20 !text-status-warning'"
          >
            {{ authenticated ? '已登录' : '未登录' }}
          </el-tag>
          <el-button size="small" :type="authenticated ? 'danger' : 'primary'" plain @click="authenticated ? handleLogout() : handleAuthNavigate()">
            {{ authenticated ? '退出登录' : '前往登录' }}
          </el-button>
        </div>
      </el-header>

      <el-main class="p-8 overflow-auto relative z-0 bg-surface-page">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Calendar,
  Coin,
  Cpu,
  DataBoard,
  Expand,
  Fold,
  List,
  Refresh,
  Setting,
  Tickets,
  User,
} from '@element-plus/icons-vue'
import request from '../utils/httpClient'
import type { ScheduleRunResponse } from '../types/apiModels'
import {
  AUTH_CHANGED_EVENT_NAME,
  clearAuthSession,
  ensureAuthSession,
  getAuthSessionState,
  normalizeAuthRedirectPath,
} from '../utils/authSession'
import { showStructuredConfirmDialog } from '../utils/confirmDialog'
import { getRouteAccessRequirement, hasAccessRequirement } from '../utils/accessControl'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)
const scheduleRunning = ref(false)
const sessionState = ref(getAuthSessionState())

const syncSessionState = () => {
  sessionState.value = getAuthSessionState()
}

const initializeAuthSession = async () => {
  await ensureAuthSession({ forceRefresh: true })
  syncSessionState()
}

const handleWindowFocus = () => {
  void initializeAuthSession()
}

const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') {
    void initializeAuthSession()
  }
}

const buildLoginRedirect = () => {
  return normalizeAuthRedirectPath(route.fullPath)
}

const handleAuthNavigate = () => {
  return router.push({
    name: 'AdminAuth',
    query: { redirect: buildLoginRedirect() },
  })
}

const handleLogout = async () => {
  try {
    await request.post('/api/auth/logout', {}, { silentError: true })
  } finally {
    clearAuthSession()
    ElMessage.success('已退出登录')
    await router.replace({
      name: 'AdminAuth',
      query: { redirect: buildLoginRedirect() },
    })
  }
}

const handleRunSchedule = async () => {
  if (
    !(await ensureAuthSession({
      forceRefresh: true,
      requiredPermissions: ['schedule.manage'],
    }))
  ) {
    syncSessionState()
    if (!authenticated.value) {
      await handleAuthNavigate()
      return
    }
    ElMessage.warning('当前账号无执行排产权限')
    return
  }
  syncSessionState()
  try {
    await showStructuredConfirmDialog({
      title: '一键排产确认',
      badge: '执行排产',
      headline: '确认立即执行一键排产吗？',
      description: '系统将按当前规则重新生成排产结果，请确认前置数据已经同步完成。',
      confirmButtonText: '确认执行',
      cancelButtonText: '取消',
      type: 'warning',
      customClass: 'app-confirm-message-box--sync',
    })
  } catch {
    return
  }

  scheduleRunning.value = true
  try {
    const res = await request.post<ScheduleRunResponse>('/api/admin/schedule/run', {})
    if (res.total === 0) {
      ElMessage.info(res.message || '暂无可执行的排产订单')
    } else {
      ElMessage.success(`排产完成：共 ${res.total} 条，成功 ${res.success_count} 条，失败 ${res.fail_count} 条`)
    }
  } catch (error: unknown) {
    ElMessage.error(`排产失败：${error instanceof Error ? error.message : '请稍后重试'}`)
  } finally {
    scheduleRunning.value = false
  }
}

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/schedules/')) return '/schedules'
  return path
})

const authenticated = computed(() => sessionState.value.authenticated)

const canAccessRoute = (path: string) =>
  hasAccessRequirement(sessionState.value, getRouteAccessRequirement(router.resolve(path).meta))

const canAccessDashboard = computed(() => canAccessRoute('/dashboard'))
const canAccessWorkCalendar = computed(() => canAccessRoute('/admin/work-calendar'))
const canAccessScheduleList = computed(() => canAccessRoute('/schedules'))
const canAccessPartScheduleList = computed(() => canAccessRoute('/part-schedules'))
const canAccessAssemblyTime = computed(() => canAccessRoute('/admin/assembly-times'))
const canAccessMachineCycle = computed(() => canAccessRoute('/admin/machine-cycle'))
const canAccessPartCycle = computed(() => canAccessRoute('/admin/part-cycle'))
const canAccessSyncConsole = computed(() => canAccessRoute('/admin/sync'))
const canAccessSyncLogList = computed(() => canAccessRoute('/sync-logs'))
const canAccessUserManagement = computed(() => canAccessRoute('/admin/users'))
const canAccessIssueList = computed(() => canAccessRoute('/issues'))
const canAccessSalesPlanData = computed(() => canAccessRoute('/data/sales-plan'))
const canAccessBomData = computed(() => canAccessRoute('/data/bom'))
const canAccessProductionOrderData = computed(() => canAccessRoute('/data/production-orders'))
const canAccessMachineCycleHistoryData = computed(() => canAccessRoute('/data/machine-cycle-history'))

const showBaseParamMenu = computed(
  () => canAccessAssemblyTime.value || canAccessMachineCycle.value || canAccessPartCycle.value,
)
const showSyncMenu = computed(() => canAccessSyncConsole.value || canAccessSyncLogList.value)
const showSystemMenu = computed(() => canAccessUserManagement.value || canAccessIssueList.value)
const showManagementMenus = computed(
  () => showBaseParamMenu.value || showSyncMenu.value || showSystemMenu.value,
)
const showDataMenu = computed(
  () =>
    canAccessSalesPlanData.value ||
    canAccessBomData.value ||
    canAccessProductionOrderData.value ||
    canAccessMachineCycleHistoryData.value,
)

const canRunSchedule = computed(() =>
  hasAccessRequirement(sessionState.value, {
    requiredPermissions: ['schedule.manage'],
  }),
)

onMounted(() => {
  window.addEventListener(AUTH_CHANGED_EVENT_NAME, syncSessionState)
  window.addEventListener('focus', handleWindowFocus)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  void initializeAuthSession()
})

onUnmounted(() => {
  window.removeEventListener(AUTH_CHANGED_EVENT_NAME, syncSessionState)
  window.removeEventListener('focus', handleWindowFocus)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.menu-section {
  @apply px-2 mb-2 text-[11px] font-semibold tracking-[0.22em] uppercase text-text-muted;
}

.brand-badge {
  width: 48px;
  height: 48px;
  border-radius: 13px;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.brand-mark {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  filter: drop-shadow(0 5px 12px rgba(120, 215, 137, 0.16));
}

.brand-mark svg {
  width: 100%;
  height: 100%;
  display: block;
}

.brand-title {
  color: #ffffff;
  font-size: 20px;
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.03em;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.04);
}

.menu-item {
  border-radius: 14px;
  margin-bottom: 6px;
}

.el-menu-item.is-active {
  background-color: rgba(130, 214, 149, 0.12) !important;
  color: #82d695 !important;
  font-weight: 600;
}

.el-menu-item:hover,
:deep(.el-sub-menu__title:hover) {
  background-color: rgba(255, 255, 255, 0.05) !important;
  border-radius: 14px;
}

.sub-menu-item {
  border-radius: 10px;
  margin: 3px 10px 3px 22px;
  height: 40px;
  line-height: 40px;
}

.quick-entry-card {
  background: #171918;
  border: 1px solid #2a2e2d;
  border-radius: 18px;
  padding: 18px 16px 14px;
  text-align: center;
}

.quick-entry-card__icon {
  width: 44px;
  height: 44px;
  margin: 0 auto 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  color: #82d695;
  border: 1px solid rgba(130, 214, 149, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
}

.quick-entry-card__title {
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.quick-entry-card__desc {
  margin: 6px 0 16px;
  color: #7a848b;
  font-size: 12px;
  line-height: 1.5;
}

.header-toggle {
  width: 34px;
  height: 34px;
  padding: 0;
  min-width: 34px;
  border: none !important;
  background: transparent !important;
  color: #a0aab2 !important;
}

.header-toggle:hover {
  color: #fff !important;
  background: rgba(255, 255, 255, 0.04) !important;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #2a2e2d;
  border-radius: 999px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>




