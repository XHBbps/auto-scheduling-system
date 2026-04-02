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
const formatToBeijingParts = (dateStr: string): string | null => {
  // 已带时区偏移（如 +08:00）或 Z 后缀的直接解析；无后缀的视为 UTC 附加 Z
  let normalized = dateStr
  if (dateStr.includes('T') && !dateStr.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(dateStr)) {
    normalized = `${dateStr}Z`
  }
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
 * 时间戳格式化：转为北京时间，展示为 YYYY-MM-DD HH:mm:ss。
 * 支持 UTC naive、带 Z 后缀、带时区偏移（如 +08:00）的输入。
 */
export const formatDateTime = (dateStr?: string | null): string => {
  if (!dateStr) return '-'
  const result = formatToBeijingParts(dateStr)
  return result ?? dateStr.replace('T', ' ').substring(0, 19)
}

// formatDateTimeFull 与 formatDateTime 统一为含秒格式
export const formatDateTimeFull = formatDateTime

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
