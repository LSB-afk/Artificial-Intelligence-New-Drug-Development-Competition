export function formatDuration(durationMs?: number) {
  if (durationMs === undefined) return '미실행'
  if (durationMs < 1000) return `${durationMs}ms`
  if (durationMs < 60000) return `${(durationMs / 1000).toFixed(durationMs < 10000 ? 1 : 0)}s`
  const minutes = Math.floor(durationMs / 60000)
  const seconds = Math.floor((durationMs % 60000) / 1000)
  return `${minutes}m ${String(seconds).padStart(2, '0')}s`
}

export function formatDateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('ko-KR', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date)
}

export function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date)
}

export function downloadText(filename: string, content: string, mimeType = 'text/plain;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([content], { type: mimeType }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}
