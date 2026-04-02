<template>
  <div class="space-y-6">
    <IssueManagementSearchPanel
      v-model:search-form="searchForm"
      :issue-status-map="ISSUE_STATUS_MAP"
      :issue-type-options="issueTypeOptions"
      :on-handle-search="handleSearch"
      :on-handle-reset="handleReset"
    />

    <IssueManagementTableSection
      v-model:page-no="pageNo"
      v-model:page-size="pageSize"
      :can-manage-issues="canManageIssues"
      :loading="loading"
      :on-fetch-data="fetchData"
      :on-handle-action="handleAction"
      :on-handle-table-sort-change="handleTableSortChange"
      :on-handle-table-state-action="handleTableStateAction"
      :page-sizes="pageSizes"
      :sortable-column-props="sortableColumnProps"
      :table-data="tableData"
      :table-feedback-state="tableFeedbackState"
      :total="total"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import IssueManagementSearchPanel from '../components/issue-management/IssueManagementSearchPanel.vue'
import IssueManagementTableSection from '../components/issue-management/IssueManagementTableSection.vue'
import { ISSUE_STATUS_MAP } from '../constants/enums'
import { useRemoteTableQuery } from '../composables/useServerTableQuery'
import { createTableStateActionHandler } from '../composables/useTableFeedbackState'
import request from '../utils/httpClient'
import type { PaginatedResponse, IssueItem } from '../types/apiModels'
import { AUTH_CHANGED_EVENT_NAME, getAuthSessionState } from '../utils/authSession'
import { hasPermissionCode } from '../utils/accessControl'
import { showStructuredConfirmDialog } from '../utils/confirmDialog'

const router = useRouter()
const route = useRoute()

type IssueManagementSearchForm = Record<string, string> & {
  issue_type: string
  status: string
  bizKey: string
  sourceSystem: string
}

const createSearchForm = (): IssueManagementSearchForm => ({
  issue_type: '',
  status: '',
  bizKey: '',
  sourceSystem: '',
})

const {
  sortableColumnProps,
  tableFeedbackState,
  loading,
  tableData,
  searchForm,
  pageNo,
  pageSize,
  pageSizes,
  total,
  fetchData,
  handleSearch,
  handleReset,
  handleTableSortChange,
} = useRemoteTableQuery<IssueManagementSearchForm, IssueItem, PaginatedResponse<IssueItem>>({
  createSearchForm,
  perfScope: 'issueManagement',
  perfLabel: 'fetchIssueTable',
  buildPerfMeta: (params) => ({
    hasIssueType: Boolean(params.issue_type),
    hasStatus: Boolean(params.status),
    hasBizKey: Boolean(params.biz_key),
    hasSourceSystem: Boolean(params.source_system),
  }),
  searchParamKeyMap: {
    bizKey: 'biz_key',
    sourceSystem: 'source_system',
  },
  sortFieldMap: {
    created_at: 'created_at',
    issue_type: 'issue_type',
    issue_level: 'issue_level',
    source_system: 'source_system',
    issue_title: 'issue_title',
  },
  request: (params) =>
    request.get<PaginatedResponse<IssueItem>>('/api/issues', {
      params,
      silentError: true,
    }),
})

const issueTypeOptions = ref<string[]>([])
const sessionState = ref(getAuthSessionState())

const syncSessionState = () => {
  sessionState.value = getAuthSessionState()
}

const canManageIssues = computed(() => hasPermissionCode(sessionState.value, "issue.manage"))

const handleTableStateAction = createTableStateActionHandler({
  tableFeedbackState,
  retry: fetchData,
  router,
  redirectPath: route.fullPath,
})

const fetchIssueTypeOptions = async () => {
  try {
    const res = await request.get('/api/issues/options/issue-types')
    issueTypeOptions.value = res || []
  } catch (error) {
    console.error(error)
  }
}

const handleAction = async (id: number, action: 'resolve' | 'ignore') => {
  if (!canManageIssues.value) {
    ElMessage.error('当前账号无处理异常权限')
    return
  }

  const actionLabel = action === 'resolve' ? '处理' : '忽略'
  try {
    await showStructuredConfirmDialog({
      title: `确认${actionLabel}异常`,
      headline: `确认${actionLabel}该异常记录？`,
      description: action === 'ignore' ? '忽略后该异常将不再展示，此操作不可撤销。' : '处理后该异常将标记为已解决。',
      confirmButtonText: `确认${actionLabel}`,
      type: 'warning',
    })
  } catch {
    return
  }

  try {
    await request.post(`/api/admin/issues/${id}/${action}`)
    ElMessage.success('操作成功')
    await fetchData()
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  window.addEventListener(AUTH_CHANGED_EVENT_NAME, syncSessionState)
  void fetchIssueTypeOptions()
  void fetchData()
})

onUnmounted(() => {
  window.removeEventListener(AUTH_CHANGED_EVENT_NAME, syncSessionState)
})
</script>



