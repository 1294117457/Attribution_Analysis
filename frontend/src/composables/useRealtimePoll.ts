/**
 * 实时数据轮询（配合后端实时接口的 15 秒缓存）
 *
 * - 只在交易时段（北京时间工作日 09:25–11:30、13:00–15:00）且页面可见时轮询
 * - 切回页面立即刷新一次；组件卸载 / enabled=false 时停止
 * - 上一次请求未返回则跳过本轮；连续失败 3 次后暂停，调用 resume() 继续
 *
 * 首次加载由调用方负责（loader 自己决定是否显示 loading），这里只管后续刷新。
 *
 * 配套设计文档：backend/docs/dev/step2/04采集管理优化/06实时数据接口.md §6.2
 */
import { onBeforeUnmount, ref, unref, watch, type Ref } from 'vue'

const MAX_FAILURES = 3

export function isTradingTime(now: Date = new Date()): boolean {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(now)
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? ''
  if (get('weekday') === 'Sat' || get('weekday') === 'Sun') return false
  const hm = Number(get('hour')) * 60 + Number(get('minute'))
  return (hm >= 9 * 60 + 25 && hm < 11 * 60 + 30) || (hm >= 13 * 60 && hm < 15 * 60)
}

export function useRealtimePoll(
  loader: () => Promise<void>,
  options: { interval: Ref<number> | number; enabled?: Ref<boolean> },
) {
  const paused = ref(false)
  const trading = ref(isTradingTime())
  let timer: ReturnType<typeof setInterval> | null = null
  let inFlight = false
  let failures = 0

  const enabled = () => (options.enabled ? options.enabled.value : true)

  async function tick() {
    trading.value = isTradingTime()
    if (!enabled() || paused.value || inFlight) return
    if (!trading.value || document.visibilityState !== 'visible') return
    inFlight = true
    try {
      await loader()
      failures = 0
    } catch {
      failures += 1
      if (failures >= MAX_FAILURES) paused.value = true
    } finally {
      inFlight = false
    }
  }

  function start() {
    stop()
    timer = setInterval(tick, unref(options.interval))
  }

  function stop() {
    if (timer) clearInterval(timer)
    timer = null
  }

  function resume() {
    failures = 0
    paused.value = false
    tick()
  }

  function onVisibility() {
    if (document.visibilityState === 'visible') tick()
  }

  document.addEventListener('visibilitychange', onVisibility)
  watch(
    () => [enabled(), unref(options.interval)],
    ([on]) => (on ? start() : stop()),
    { immediate: true },
  )

  onBeforeUnmount(() => {
    stop()
    document.removeEventListener('visibilitychange', onVisibility)
  })

  return { paused, trading, resume }
}
