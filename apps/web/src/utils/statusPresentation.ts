import { ISSUE_STATUS_MAP, SCHEDULE_STATUS_MAP, WARNING_LEVEL_MAP } from '../constants/enums'
import { BUSINESS_TERMS } from '../constants/terminology'

export type StatusBadgeTone =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'primary'
  | 'neutral'
  | 'cyan'
  | 'purple'
  | 'orange'
  | 'blue'

export interface StatusBadgeMeta {
  label: string
  tone: StatusBadgeTone
  minWidth?: number
  title?: string
}

const BADGE_MIN_WIDTH = {
  flag: 64,
  level: 60,
  status: 72,
  syncStatus: 76,
  schedule: 82,
  type: 72,
}

const resolveEnumTone = (color?: string): StatusBadgeTone => {
  if (color === 'success') return 'success'
  if (color === 'warning') return 'warning'
  if (color === 'danger') return 'danger'
  if (color === 'primary') return 'primary'
  return 'info'
}

const buildMeta = (label: string, tone: StatusBadgeTone, minWidth: number): StatusBadgeMeta => ({
  label,
  tone,
  minWidth,
  title: label,
})

const CATEGORICAL_BADGE_TONES: StatusBadgeTone[] = [
  'cyan',
  'blue',
  'purple',
  'primary',
  'success',
  'warning',
  'orange',
  'info',
]

const normalizeBadgeValue = (value?: string | null) => value?.trim() || ''

const getStableToneByText = (text: string, namespace: string): StatusBadgeTone => {
  const seed = `${namespace}:${text}`
  let hash = 0
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) >>> 0
  }
  return CATEGORICAL_BADGE_TONES[hash % CATEGORICAL_BADGE_TONES.length]
}

const getStableCategoricalBadgeMeta = (
  value: string | null | undefined,
  namespace: string,
  minWidth = BADGE_MIN_WIDTH.status,
): StatusBadgeMeta => {
  const normalized = normalizeBadgeValue(value)
  if (!normalized) return buildMeta('-', 'neutral', minWidth)
  return buildMeta(normalized, getStableToneByText(normalized, namespace), minWidth)
}

export const getScheduleStatusBadgeMeta = (value?: string | null): StatusBadgeMeta => {
  const normalized = value || ''
  const meta = normalized ? SCHEDULE_STATUS_MAP[normalized] : undefined
  return buildMeta(meta?.label || value || '-', resolveEnumTone(meta?.color), BADGE_MIN_WIDTH.schedule)
}

export const getWarningLevelBadgeMeta = (value?: string | null): StatusBadgeMeta => {
  const normalized = value || ''
  const meta = normalized ? WARNING_LEVEL_MAP[normalized] : undefined
  return buildMeta(meta?.label || value || '-', resolveEnumTone(meta?.color), BADGE_MIN_WIDTH.level)
}

export const getIssueStatusBadgeMeta = (value?: string | null): StatusBadgeMeta => {
  const normalized = value || ''
  const meta = normalized ? ISSUE_STATUS_MAP[normalized] : undefined
  return buildMeta(meta?.label || value || '-', resolveEnumTone(meta?.color), BADGE_MIN_WIDTH.status)
}

export const getIssueLevelBadgeMeta = (value?: string | null): StatusBadgeMeta => {
  const normalized = (value || '').toLowerCase()
  if (normalized === 'high') return buildMeta('高', 'danger', BADGE_MIN_WIDTH.level)
  if (normalized === 'medium') return buildMeta('中', 'warning', BADGE_MIN_WIDTH.level)
  if (normalized === 'low') return buildMeta('低', 'neutral', BADGE_MIN_WIDTH.level)
  return buildMeta(value || '-', 'neutral', BADGE_MIN_WIDTH.level)
}

export const getDrawingReleasedBadgeMeta = (
  value?: boolean | null,
  trueLabel = '已发图',
  falseLabel = '未发图',
): StatusBadgeMeta => buildMeta(value ? trueLabel : falseLabel, value ? 'success' : 'warning', BADGE_MIN_WIDTH.flag)

export const getOrderTypeBadgeMeta = (value?: string | null): StatusBadgeMeta => {
  const normalized = value || ''
  if (normalized === '1') return buildMeta('\u5e38\u89c4', 'neutral', BADGE_MIN_WIDTH.type)
  if (normalized === '2') return buildMeta('\u9009\u914d', 'warning', BADGE_MIN_WIDTH.type)
  if (normalized === '3') return buildMeta('\u5b9a\u5236', 'primary', BADGE_MIN_WIDTH.type)
  return buildMeta(value || '-', 'neutral', BADGE_MIN_WIDTH.type)
}

export const getBusinessGroupBadgeMeta = (value?: string | null): StatusBadgeMeta =>
  getStableCategoricalBadgeMeta(value, 'business_group', BADGE_MIN_WIDTH.status)

export const getSalesBranchCompanyBadgeMeta = (value?: string | null): StatusBadgeMeta =>
  getStableCategoricalBadgeMeta(value, 'sales_branch_company', BADGE_MIN_WIDTH.status)

export const getSalesSubBranchBadgeMeta = (value?: string | null): StatusBadgeMeta =>
  getStableCategoricalBadgeMeta(value, 'sales_sub_branch', BADGE_MIN_WIDTH.status)

export const getDefaultValueBadgeMeta = (value?: boolean | null): StatusBadgeMeta =>
  buildMeta(value ? '默认' : '非默认', value ? 'warning' : 'neutral', BADGE_MIN_WIDTH.status)

export const getActiveStatusBadgeMeta = (value?: boolean | null): StatusBadgeMeta =>
  buildMeta(value ? '启用' : '停用', value ? 'success' : 'neutral', BADGE_MIN_WIDTH.status)

export const getSyncJobStatusBadgeMeta = (value?: string | null): StatusBadgeMeta => {
  const normalized = value || ''
  if (normalized === 'completed') return buildMeta('已完成', 'success', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'completed_with_errors') return buildMeta(BUSINESS_TERMS.completedWithWarnings, 'warning', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'running') return buildMeta('执行中', 'primary', BADGE_MIN_WIDTH.syncStatus)
  return buildMeta(value || '-', 'neutral', BADGE_MIN_WIDTH.syncStatus)
}

export const getSyncViewStatusBadgeMeta = (
  value?: 'idle' | 'queued' | 'running' | 'success' | 'error' | 'noop' | null,
): StatusBadgeMeta => {
  const normalized = value || 'idle'
  if (normalized === 'idle') return buildMeta('待执行', 'neutral', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'queued') return buildMeta('已排队', 'info', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'running') return buildMeta('执行中', 'warning', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'success') return buildMeta('已完成', 'success', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'noop') return buildMeta('无需执行', 'neutral', BADGE_MIN_WIDTH.syncStatus)
  return buildMeta('失败', 'danger', BADGE_MIN_WIDTH.syncStatus)
}

export const getQueueStatusBadgeMeta = (value?: string | null): StatusBadgeMeta => {
  const normalized = value || ''
  if (normalized === 'pending') return buildMeta('待处理', 'neutral', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'processing') return buildMeta('处理中', 'primary', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'retry_wait') return buildMeta('待重试', 'warning', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'success') return buildMeta('成功', 'success', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'failed') return buildMeta('失败', 'danger', BADGE_MIN_WIDTH.syncStatus)
  if (normalized === 'paused') return buildMeta('已暂停', 'neutral', BADGE_MIN_WIDTH.syncStatus)
  return buildMeta(value || '-', 'neutral', BADGE_MIN_WIDTH.syncStatus)
}

export const getSchedulerStateBadgeMeta = (value?: string | null): StatusBadgeMeta => {
  const normalized = value || ''
  if (normalized === 'running') return buildMeta('调度器运行中', 'success', 104)
  if (normalized === 'paused') return buildMeta('调度器已暂停', 'neutral', 104)
  if (normalized === 'stopped') return buildMeta('调度器已停止', 'warning', 104)
  return buildMeta('状态未知', 'neutral', 104)
}

export const getPartTypeBadgeMeta = (partType?: string | null, bomLevel?: number | null): StatusBadgeMeta => {
  const label = partType || '-'
  if (bomLevel === 0 || partType?.includes('整机')) return buildMeta(label, 'cyan', BADGE_MIN_WIDTH.type)
  if (!partType) return buildMeta(label, 'neutral', BADGE_MIN_WIDTH.type)
  if (partType.includes('虚拟')) return buildMeta(label, 'purple', BADGE_MIN_WIDTH.type)
  if (partType.includes('自产')) return buildMeta(label, 'success', BADGE_MIN_WIDTH.type)
  if (partType.includes('外购')) return buildMeta(label, 'warning', BADGE_MIN_WIDTH.type)
  if (partType.includes('外协')) return buildMeta(label, 'orange', BADGE_MIN_WIDTH.type)
  if (partType.includes('互协')) return buildMeta(label, 'blue', BADGE_MIN_WIDTH.type)
  if (partType.includes('其他')) return buildMeta(label, 'neutral', BADGE_MIN_WIDTH.type)
  return buildMeta(label, 'neutral', BADGE_MIN_WIDTH.type)
}

export const getSystemBuiltInBadgeMeta = (value?: boolean | null): StatusBadgeMeta =>
  buildMeta(value ? '系统内置' : '自定义', value ? 'primary' : 'neutral', BADGE_MIN_WIDTH.status)

