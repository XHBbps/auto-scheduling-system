export type PerfStatus = 'success' | 'error' | 'noop'

export interface PerfMetric {
  scope: string
  label: string
  durationMs: number
  status: PerfStatus
  at: string
  meta?: Record<string, unknown>
}

declare global {
  interface Window {
    __SOUL_PERF_METRICS__?: PerfMetric[]
  }
}

const MAX_METRICS = 200
const PERF_DEBUG_STORAGE_KEY = 'soul-perf-debug'

const isPerfDebugEnabled = () => {
  if (typeof window === 'undefined') return false
  try {
    return window.localStorage.getItem(PERF_DEBUG_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export const recordPerfMetric = (metric: PerfMetric) => {
  if (typeof window === 'undefined') return

  const queue = window.__SOUL_PERF_METRICS__ || []
  queue.push(metric)
  if (queue.length > MAX_METRICS) {
    queue.splice(0, queue.length - MAX_METRICS)
  }
  window.__SOUL_PERF_METRICS__ = queue

  if (import.meta.env.DEV || isPerfDebugEnabled()) {
    console.info(`[perf] ${metric.scope}:${metric.label}`, metric)
  }
}

export const measureAsync = async <T>(
  scope: string,
  label: string,
  task: () => Promise<T>,
  meta?: Record<string, unknown>,
): Promise<T> => {
  const start = performance.now()
  try {
    const result = await task()
    recordPerfMetric({
      scope,
      label,
      durationMs: Number((performance.now() - start).toFixed(2)),
      status: 'success',
      at: new Date().toISOString(),
      meta,
    })
    return result
  } catch (error) {
    recordPerfMetric({
      scope,
      label,
      durationMs: Number((performance.now() - start).toFixed(2)),
      status: 'error',
      at: new Date().toISOString(),
      meta: {
        ...meta,
        error: error instanceof Error ? error.message : String(error),
      },
    })
    throw error
  }
}

export const recordPerfPoint = (
  scope: string,
  label: string,
  durationMs: number,
  status: PerfStatus = 'success',
  meta?: Record<string, unknown>,
) => {
  recordPerfMetric({
    scope,
    label,
    durationMs: Number(durationMs.toFixed(2)),
    status,
    at: new Date().toISOString(),
    meta,
  })
}
