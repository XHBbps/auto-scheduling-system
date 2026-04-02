import type { AxiosResponse } from 'axios'

export type BlobDownloadResponse = Blob | AxiosResponse<Blob>

const stripQuotes = (value: string) => value.replace(/^"(.*)"$/, '$1').trim()

const parseFilenameFromContentDisposition = (contentDisposition?: string | null) => {
  if (!contentDisposition) return ''

  const utf8Match = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(stripQuotes(utf8Match[1]))
    } catch {
      return stripQuotes(utf8Match[1])
    }
  }

  const filenameMatch = contentDisposition.match(/filename\s*=\s*([^;]+)/i)
  if (filenameMatch?.[1]) {
    return stripQuotes(filenameMatch[1])
  }

  return ''
}

const isAxiosBlobResponse = (value: BlobDownloadResponse): value is AxiosResponse<Blob> => {
  return typeof value === "object" && value !== null && 'data' in value && 'headers' in value
}

/**
 * 下载 blob 文件
 */
export const downloadBlob = (input: BlobDownloadResponse, fallbackFilename: string) => {
  const blob = isAxiosBlobResponse(input) ? input.data : input
  const responseFilename = isAxiosBlobResponse(input)
    ? parseFilenameFromContentDisposition(input.headers?.['content-disposition'])
    : ''
  const filename = responseFilename || fallbackFilename

  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  setTimeout(() => window.URL.revokeObjectURL(url), 200)
}
