import type { CollectTask } from '../api'

/** 采集任务列表（接口任务列表 / 采集历史）共用的格式化工具 */

export type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

export const STATUS_OPTIONS: { label: string; value: string }[] = [
  { label: '采集中', value: 'running' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
  { label: '已取消', value: 'cancelled' },
  { label: '等待中', value: 'pending' },
]

export function statusLabel(s: string): string {
  return STATUS_OPTIONS.find((o) => o.value === s)?.label || s
}

export function statusColor(s: string): TagType {
  const map: Record<string, TagType> = {
    pending: 'info', running: 'primary', success: 'success', failed: 'danger', cancelled: 'info',
  }
  return map[s] || 'info'
}

export function formatParams(task: CollectTask): string {
  if (!task.params) return '-'
  const p = task.params
  const parts: string[] = []
  if (p.mode === 'full') parts.push('全量')
  else if (p.mode === 'condition') parts.push('条件')
  if (Array.isArray(p.exchange) && p.exchange.length > 0) {
    parts.push(p.exchange.join('/'))
  }
  if (p.start_date && p.end_date) {
    const s = String(p.start_date).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
    const e = String(p.end_date).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
    parts.push(`${s} ~ ${e}`)
  } else if (p.days != null) {
    parts.push(`回溯${p.days}天`)
  } else if (p.years != null) {
    parts.push(`回溯${p.years}年`)
  }
  if (p.concurrency != null && p.concurrency > 1) {
    parts.push(`并发×${p.concurrency}`)
  }
  if (p.limit != null) {
    parts.push(`前${p.limit}`)
  }
  if (p.full) parts.push('全量重写')
  if (p.only_missing) parts.push('仅缺失')
  if (p.list_status) parts.push(`状态: ${p.list_status}`)
  return parts.length > 0 ? parts.join(' · ') : '-'
}

export function formatDuration(ms: number | null): string {
  if (ms == null || ms <= 0) return '-'
  const totalSec = Math.floor(ms / 1000)
  if (totalSec < 60) return `${totalSec}s`
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  if (min < 60) return sec > 0 ? `${min}m${sec}s` : `${min}m`
  const hr = Math.floor(min / 60)
  const rm = min % 60
  return rm > 0 ? `${hr}h${rm}m` : `${hr}h`
}

export function formatTime(v: string | null): string {
  if (!v) return '-'
  return v.replace('T', ' ').replace(/\.\d+$/, '').slice(0, 19)
}
