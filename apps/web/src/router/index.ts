import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
  type Router,
  type RouterHistory,
} from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import { ensureAuthSession, normalizeAuthRedirectPath } from '../utils/authSession'
import { getRouteAccessRequirement } from '../utils/accessControl'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    public?: boolean
    requiredRoles?: string[]
    requiredPermissions?: string[]
    requiredAnyPermissions?: string[]
  }
}

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/ScheduleDashboardPage.vue'),
        meta: { title: '排产总览', requiredPermissions: ['schedule.view'] },
      },
      {
        path: 'schedules',
        name: 'ScheduleList',
        component: () => import('../views/MachineScheduleListPage.vue'),
        meta: { title: '整机排产列表', requiredPermissions: ['schedule.view'] },
      },
      {
        path: 'part-schedules',
        name: 'PartScheduleList',
        component: () => import('../views/PartScheduleListPage.vue'),
        meta: { title: '零部件排产列表', requiredPermissions: ['schedule.view'] },
      },
      {
        path: 'schedules/:id',
        name: 'ScheduleDetail',
        component: () => import('../views/MachineScheduleDetailPage.vue'),
        meta: { title: '排产详情', requiredPermissions: ['schedule.view'] },
      },
      {
        path: 'issues',
        name: 'IssueList',
        component: () => import('../views/IssueManagementPage.vue'),
        meta: { title: '异常问题', requiredPermissions: ['issue.view'] },
      },
      {
        path: 'sync-logs',
        name: 'SyncLogList',
        component: () => import('../views/SyncLogListPage.vue'),
        meta: { title: '同步日志', requiredPermissions: ['sync.log.view'] },
      },
      {
        path: 'admin/assembly-times',
        name: 'AssemblyTime',
        component: () => import('../views/AssemblyTimeConfigPage.vue'),
        meta: { title: '装配时长配置', requiredPermissions: ['settings.manage'] },
      },
      {
        path: 'admin/machine-cycle',
        name: 'MachineCycleBaseline',
        component: () => import('../views/MachineCycleBaselinePage.vue'),
        meta: { title: '整机周期基准', requiredPermissions: ['settings.manage'] },
      },
      {
        path: 'admin/part-cycle',
        name: 'PartCycleBaseline',
        component: () => import('../views/PartCycleBaselinePage.vue'),
        meta: { title: '零件周期基准', requiredPermissions: ['settings.manage'] },
      },
      {
        path: 'admin/work-calendar',
        name: 'WorkCalendar',
        component: () => import('../views/WorkCalendarPage.vue'),
        meta: { title: '排产日历', requiredPermissions: ['settings.manage'] },
      },
      {
        path: 'admin/sync',
        name: 'SyncStatus',
        component: () => import('../views/SyncConsolePage.vue'),
        meta: { title: '数据同步', requiredPermissions: ['sync.manage'] },
      },
      {
        path: 'admin/users',
        name: 'UserManagement',
        component: () => import('../views/UserManagementPage.vue'),
        meta: { title: '用户管理', requiredAnyPermissions: ['user.view', 'role.view', 'permission.view'] },
      },
      {
        path: 'data/sales-plan',
        name: 'DataSalesPlan',
        component: () => import('../views/SalesPlanDataPage.vue'),
        meta: { title: '销售计划表', requiredPermissions: ['data_source.view'] },
      },
      {
        path: 'data/bom',
        name: 'DataBom',
        component: () => import('../views/BomDataPage.vue'),
        meta: { title: 'BOM 数据', requiredPermissions: ['data_source.view'] },
      },
      {
        path: 'data/production-orders',
        name: 'DataProductionOrder',
        component: () => import('../views/ProductionOrderDataPage.vue'),
        meta: { title: '生产订单历史', requiredPermissions: ['data_source.view'] },
      },
      {
        path: 'data/machine-cycle-history',
        name: 'DataMachineCycleHistory',
        component: () => import('../views/MachineCycleHistoryDataPage.vue'),
        meta: { title: '整机周期历史', requiredPermissions: ['data_source.view'] },
      },
    ],
  },
  {
    path: '/admin-auth',
    alias: '/login',
    name: 'AdminAuth',
    component: () => import('../views/AdminAccessPage.vue'),
    meta: { title: '管理员认证', public: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFoundPage.vue'),
  },
]

export const registerAuthGuard = (router: Router) => {
  router.beforeEach(async (to) => {
    if (to.meta.public) {
      if (to.name !== 'AdminAuth') {
        return true
      }
      const passed = await ensureAuthSession()
      if (!passed) {
        return true
      }
      return normalizeAuthRedirectPath(to.query.redirect)
    }

    const accessRequirement = getRouteAccessRequirement(to.meta)
    const passed = await ensureAuthSession({
      requiredRoles: accessRequirement.requiredRoles,
      requiredPermissions: accessRequirement.requiredPermissions,
      requiredAnyPermissions: accessRequirement.requiredAnyPermissions,
    })
    if (!passed) {
      return {
        name: 'AdminAuth',
        query: { redirect: normalizeAuthRedirectPath(to.fullPath) },
      }
    }
    return true
  })
}

export const createAppRouter = (history: RouterHistory = createWebHistory()) => {
  const router = createRouter({
    history,
    routes,
  })
  registerAuthGuard(router)
  return router
}

const router = createAppRouter()

export default router
