import { onUnmounted } from 'vue'

export const useRequestCancellation = () => {
  let controller: AbortController | null = null

  const newSignal = (): AbortSignal => {
    controller?.abort()
    controller = new AbortController()
    return controller.signal
  }

  const cancel = () => {
    controller?.abort()
    controller = null
  }

  onUnmounted(cancel)

  return { newSignal, cancel }
}
