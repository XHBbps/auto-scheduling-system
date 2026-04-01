import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ensureAuthSession, getAuthSessionState } from '../utils/authSession'
import { downloadBlob, type BlobDownloadResponse } from '../utils/download'
import { showStructuredConfirmDialog } from '../utils/confirmDialog'

export interface ConfirmedExportOptions {
  confirmTitle: string
  confirmMessage: string
  fallbackFilename: string
  request: () => Promise<BlobDownloadResponse>
  successMessage?: string
  failureMessage?: string
  authFailureMessage?: string
  forbiddenMessage?: string
}

const isConfirmCanceled = (error: unknown) => error === 'cancel' || error === 'close'

export const useExportAction = () => {
  const route = useRoute()
  const router = useRouter()
  const exporting = ref(false)

  const redirectToLogin = async () => {
    await router.push({
      name: 'AdminAuth',
      query: {
        redirect: route.fullPath,
      },
    })
  }

  const runConfirmedExport = async (options: ConfirmedExportOptions) => {
    if (exporting.value) {
      return false
    }

    try {
      await showStructuredConfirmDialog({
        title: options.confirmTitle,
        badge: '导出数据',
        headline: options.confirmMessage,
        description: '系统会按当前筛选条件生成文件，并在准备完成后立即开始下载。',
        confirmButtonText: '开始导出',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch (error) {
      if (isConfirmCanceled(error)) {
        return false
      }
      throw error
    }

    if (!(await ensureAuthSession({ forceRefresh: true, requiredPermissions: ['export.view'] }))) {
      const authState = getAuthSessionState()
      if (!authState.authenticated) {
        await redirectToLogin()
        return false
      }
      ElMessage.error(options.forbiddenMessage || '当前账号无权限导出所选数据')
      return false
    }

    exporting.value = true
    try {
      const response = await options.request()
      downloadBlob(response, options.fallbackFilename)
      ElMessage.success(options.successMessage || '导出成功，已开始下载文件')
      return true
    } catch (error) {
      console.error(error)
      const status = (error as Error & { status?: number })?.status

      if (status === 401) {
        ElMessage.error(options.authFailureMessage || '登录状态已失效，请重新登录后再导出')
        await redirectToLogin()
        return false
      }

      if (status === 403) {
        ElMessage.error(options.forbiddenMessage || '当前账号无权限导出所选数据')
        return false
      }

      ElMessage.error(options.failureMessage || '导出失败，请稍后重试')
      return false
    } finally {
      exporting.value = false
    }
  }

  return {
    exporting,
    runConfirmedExport,
  }
}
