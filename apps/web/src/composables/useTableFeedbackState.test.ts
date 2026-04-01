import { vi, describe, expect, it } from 'vitest'
import { createTableStateActionHandler, useTableFeedbackState } from './useTableFeedbackState'

describe('useTableFeedbackState', () => {
  it('maps 401 to auth and 403 to forbidden', () => {
    const { tableFeedbackState, showErrorState } = useTableFeedbackState()

    const authError = Object.assign(new Error('401'), { status: 401 })
    showErrorState(authError)
    expect(tableFeedbackState.value).toBe('auth')

    const forbiddenError = Object.assign(new Error('403'), { status: 403 })
    showErrorState(forbiddenError)
    expect(tableFeedbackState.value).toBe('forbidden')
  })

  it('supports loading empty and disabled state transitions', () => {
    const { tableFeedbackState, showLoadingState, showEmptyState, showDisabledState } = useTableFeedbackState()

    showLoadingState()
    expect(tableFeedbackState.value).toBe('loading')

    showEmptyState()
    expect(tableFeedbackState.value).toBe('empty')

    showDisabledState()
    expect(tableFeedbackState.value).toBe('disabled')
  })

  it('retries on error action and redirects on auth action', async () => {
    const retry = vi.fn()
    const router = {
      push: vi.fn().mockResolvedValue(undefined),
    }
    const { tableFeedbackState, showErrorState } = useTableFeedbackState()
    const handleAction = createTableStateActionHandler({
      tableFeedbackState,
      retry,
      router: router as any,
      redirectPath: '/issues',
    })

    showErrorState(new Error('boom'))
    await handleAction()
    expect(retry).toHaveBeenCalledTimes(1)

    showErrorState(Object.assign(new Error('401'), { status: 401 }))
    await handleAction()
    expect(router.push).toHaveBeenCalledWith({
      name: 'AdminAuth',
      query: {
        redirect: '/issues',
      },
    })
  })
})
