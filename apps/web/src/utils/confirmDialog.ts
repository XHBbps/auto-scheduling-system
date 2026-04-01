import { ElMessageBox } from 'element-plus'
import { h, type VNode } from 'vue'

export interface StructuredConfirmDialogOptions {
  title: string
  badge?: string
  headline: string
  description?: string
  confirmButtonText?: string
  cancelButtonText?: string
  type?: 'success' | 'warning' | 'info' | 'error'
  customClass?: string
}

/**
 * Build a VNode for the confirm dialog message.
 * Uses Vue's h() to avoid dangerouslyUseHTMLString and XSS risk.
 */
const renderConfirmMessage = (options: StructuredConfirmDialogOptions): VNode => {
  const children: VNode[] = []

  if (options.badge) {
    children.push(h('div', { class: 'app-confirm-message-box__badge' }, options.badge))
  }
  children.push(h('div', { class: 'app-confirm-message-box__headline' }, options.headline))
  if (options.description) {
    children.push(h('div', { class: 'app-confirm-message-box__description' }, options.description))
  }

  return h('div', { class: 'app-confirm-message-box__layout' }, children)
}

/**
 * Show a structured confirm dialog. Resolves on confirm, rejects with 'cancel' or 'close' on dismiss.
 */
export const showStructuredConfirmDialog = (options: StructuredConfirmDialogOptions) =>
  ElMessageBox.confirm(renderConfirmMessage(options), options.title, {
    confirmButtonText: options.confirmButtonText || '确认',
    cancelButtonText: options.cancelButtonText || '取消',
    type: options.type || 'warning',
    customClass: ['app-confirm-message-box', options.customClass].filter(Boolean).join(' '),
    showClose: false,
    closeOnClickModal: false,
    closeOnPressEscape: true,
  })
