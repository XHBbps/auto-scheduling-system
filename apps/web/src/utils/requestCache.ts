interface CacheEntry<T> {
  data?: T
  expiresAt: number
  promise?: Promise<T>
}

const MAX_CACHE_ENTRIES = 50
const requestCacheStore = new Map<string, CacheEntry<unknown>>()

export const getCachedAsync = async <T>(
  key: string,
  ttlMs: number,
  loader: () => Promise<T>,
): Promise<T> => {
  const now = Date.now()
  const cached = requestCacheStore.get(key) as CacheEntry<T> | undefined

  if (cached?.data !== undefined && cached.expiresAt > now) {
    return cached.data
  }

  if (cached?.promise) {
    return cached.promise
  }

  const promise = loader()
  // Evict oldest entries if cache exceeds limit
  if (requestCacheStore.size >= MAX_CACHE_ENTRIES) {
    const firstKey = requestCacheStore.keys().next().value
    if (firstKey !== undefined) requestCacheStore.delete(firstKey)
  }
  requestCacheStore.set(key, {
    expiresAt: now + ttlMs,
    promise,
  })

  try {
    const data = await promise
    requestCacheStore.set(key, {
      data,
      expiresAt: Date.now() + ttlMs,
    })
    return data
  } catch (error) {
    requestCacheStore.delete(key)
    throw error
  }
}

export const clearCachedRequest = (key: string) => {
  requestCacheStore.delete(key)
}

export const clearCachedRequestByPrefix = (prefix: string) => {
  for (const key of requestCacheStore.keys()) {
    if (key.startsWith(prefix)) {
      requestCacheStore.delete(key)
    }
  }
}
