import type { Ref } from 'vue'
import { ref } from 'vue'
import type { Router } from 'vue-router'
import type { MaybePromise } from './useServerTableQuery'

export type TableFeedbackState = 'loading' | 'empty' | 'error' | 'auth' | 'forbidden' | 'disabled'

const resolveStateFromError = (error: unknown): TableFeedbackState => {
  const status = typeof error === 'object' && error && 'status' in error ? (error as { status?: number }).status : undefined
  if (status === 401) return 'auth'
  if (status === 403) return 'forbidden'
  return 'error'
}

export const useTableFeedbackState = () => {
  const tableFeedbackState = ref<TableFeedbackState>('empty')

  const resetTableFeedbackState = () => {
    tableFeedbackState.value = 'empty'
  }

  const showLoadingState = () => {
    tableFeedbackState.value = 'loading'
  }

  const showEmptyState = () => {
    tableFeedbackState.value = 'empty'
  }

  const showDisabledState = () => {
    tableFeedbackState.value = 'disabled'
  }

  const showErrorState = (error: unknown) => {
    tableFeedbackState.value = resolveStateFromError(error)
  }

  return {
    tableFeedbackState,
    resetTableFeedbackState,
    showLoadingState,
    showEmptyState,
    showDisabledState,
    showErrorState,
  }
}

export interface CreateTableStateActionHandlerOptions {
  tableFeedbackState: Ref<TableFeedbackState>
  retry: () => MaybePromise
  router: Router
  redirectPath: string
}

export const createTableStateActionHandler = (
  options: CreateTableStateActionHandlerOptions,
) => {
  const { tableFeedbackState, retry, router, redirectPath } = options

  return async () => {
    if (tableFeedbackState.value === 'auth') {
      await router.push({
        name: 'AdminAuth',
        query: {
          redirect: redirectPath,
        },
      })
      return
    }

    if (tableFeedbackState.value === 'error') {
      await retry()
    }
  }
}
