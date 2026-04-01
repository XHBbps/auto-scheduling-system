
// 排产状态
export const SCHEDULE_STATUS_MAP: Record<string, { label: string; color: string }> = {
  scheduled: { label: '已排产', color: 'success' },
  scheduled_stale: { label: '待重排', color: 'warning' },
  pending_drawing: { label: '待发图', color: 'warning' },
  pending_trigger: { label: '待触发', color: 'info' },
  schedulable: { label: '可排产', color: 'primary' },
  missing_bom: { label: '缺少BOM', color: 'danger' },
}

// 异常标识
export const WARNING_LEVEL_MAP: Record<string, { label: string; color: string }> = {
  normal: { label: '正常', color: 'success' },
  abnormal: { label: '异常', color: 'danger' },
}

// 异常状态
export const ISSUE_STATUS_MAP: Record<string, { label: string; color: string }> = {
  open: { label: '待处理', color: 'danger' },
  resolved: { label: '已解决', color: 'success' },
  ignored: { label: '已忽略', color: 'info' },
}
