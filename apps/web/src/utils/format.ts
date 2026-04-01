const BEIJING_TZ = 'Asia/Shanghai'

const beijingFormatter = new Intl.DateTimeFormat('zh-CN', {
  timeZone: BEIJING_TZ,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
})

/**
 * 格式化为北京时间的 YYYY-MM-DD HH:mm:ss 格式。
 * 后端返回的时间戳为 UTC，此函数统一转换为北京时间展示。
 */
const formatToBejingParts = (dateStr: string): string | null => {
  // 后端返回的无 Z 后缀的 ISO 字符串视为 UTC
  const normalized = dateStr.includes('T') && !dateStr.endsWith('Z') ? `${dateStr}Z` : dateStr
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return null
  // Intl output: "2026/04/01 11:00:00" → reformat to "2026-04-01 11:00:00"
  return beijingFormatter.format(date).replaceAll('/', '-')
}

/**
 * 业务日期格式化：截取日期部分 (YYYY-MM-DD)。
 * 业务日期（交货期、排产日期等）本身无时区概念，直接截取。
 */
export const formatDate = (dateStr?: string | null): string => {
  if (!dateStr) return '-'
  // 纯日期字段（无 T）直接截取
  if (!dateStr.includes('T')) return dateStr.split(' ')[0]
  return dateStr.split('T')[0]
}

/**
 * 时间戳格式化：UTC → 北京时间，展示为 YYYY-MM-DD HH:mm。
 * 用于 created_at、updated_at、sync_time 等时间戳字段。
 */
export const formatDateTime = (dateStr?: string | null): string => {
  if (!dateStr) return '-'
  const result = formatToBejingParts(dateStr)
  if (!result) return dateStr.replace('T', ' ').substring(0, 16)
  // 截取到分钟：YYYY-MM-DD HH:mm
  return result.substring(0, 16)
}

/**
 * 时间戳格式化（含秒）：UTC → 北京时间，展示为 YYYY-MM-DD HH:mm:ss。
 */
export const formatDateTimeFull = (dateStr?: string | null): string => {
  if (!dateStr) return '-'
  const result = formatToBejingParts(dateStr)
  return result ?? dateStr.replace('T', ' ').substring(0, 19)
}

/**
 * 排产状态颜色映射
 */
export const getStatusColor = (status: string): string => {
  const map: Record<string, string> = {
    scheduled: '#82d695',
    pending_drawing: '#faad14',
    pending_trigger: '#717a82',
    schedulable: '#00f0ff',
  }
  return map[status] || '#717a82'
}

/**
 * 构建查询参数：移除空值
 */
export const cleanParams = (params: Record<string, any>): Record<string, any> => {
  const cleaned: Record<string, any> = {}
  Object.keys(params).forEach(key => {
    if (params[key] !== '' && params[key] !== null && params[key] !== undefined) {
      cleaned[key] = params[key]
    }
  })
  return cleaned
}
