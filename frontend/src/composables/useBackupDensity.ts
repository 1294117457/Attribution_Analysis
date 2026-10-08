/**
 * Backup 页面密度锚点 Composable（3 页面复用）
 *
 * 4 锚点：page / top / middle / bottom（-、proxy）
 * - top / middle / bottom 默认跟随 page（= null 表示 follow）
 * - 拖动时断开跟随（写入具体数值）
 * - "跟随"按钮：把 3 个 sub 全部置 null
 * - "还原"按钮：page=1、3 个 sub 全 null
 */

import { computed, ref, watch } from 'vue'

const DENSITY_KEY = 'bkup-density'

interface DensityState {
  page: number
  top: number | null
  middle: number | null
  bottom: number | null
}

function clamp(v: number, min = 0.6, max = 1.5) {
  if (!Number.isFinite(v)) return 1
  return Math.round(Math.max(min, Math.min(max, v)) * 100) / 100
}

function load(): DensityState {
  try {
    const raw = localStorage.getItem(DENSITY_KEY)
    if (!raw) return { page: 1, top: null, middle: null, bottom: null }
    const p = JSON.parse(raw)
    return {
      page: clamp(Number(p.page ?? 1)),
      top: p.top == null ? null : clamp(Number(p.top)),
      middle: p.middle == null ? null : clamp(Number(p.middle)),
      bottom: p.bottom == null ? null : clamp(Number(p.bottom)),
    }
  } catch {
    return { page: 1, top: null, middle: null, bottom: null }
  }
}

export function useBackupDensity() {
  const init = load()

  const pageDensity = ref<number>(init.page)
  const topDensity = ref<number | null>(init.top)
  const middleDensity = ref<number | null>(init.middle)
  const bottomDensity = ref<number | null>(init.bottom)

  // CSS 变量映射：sub 没变就 fall back 到 page
  const densityStyle = computed(() => {
    const s: Record<string, string> = {
      '--bkup-page-density': String(pageDensity.value),
      '--bkup-top-density': String(topDensity.value ?? pageDensity.value),
      '--bkup-middle-density': String(middleDensity.value ?? pageDensity.value),
      '--bkup-bottom-density': String(bottomDensity.value ?? pageDensity.value),
    }
    return s
  })

  // Proxy 滑块（拖动断开跟随 + colW 列宽）
  const topProxy = computed<number>({
      get: () => topDensity.value ?? pageDensity.value,
      set: (v) => (topDensity.value = v),
    })
  const midProxy = computed<number>({
      get: () => middleDensity.value ?? pageDensity.value,
      set: (v) => (middleDensity.value = v),
    })
  const botProxy = computed<number>({
      get: () => bottomDensity.value ?? pageDensity.value,
      set: (v) => (bottomDensity.value = v),
    })

  function colW(px: number): number {
    return Math.round(px * midProxy.value)
  }

  const allSynced = computed(
    () => topDensity.value === null && middleDensity.value === null && bottomDensity.value === null,
  )

  function reset() {
    pageDensity.value = 1
    topDensity.value = null
    middleDensity.value = null
    bottomDensity.value = null
  }

  function syncToPage() {
    topDensity.value = null
    middleDensity.value = null
    bottomDensity.value = null
  }

  watch(
    [pageDensity, topDensity, middleDensity, bottomDensity],
    ([p, t, m, b]) => {
      try {
        localStorage.setItem(
          DENSITY_KEY,
          JSON.stringify({
            page: p,
            top: t ?? pageDensity.value,
            middle: m ?? pageDensity.value,
            bottom: b ?? pageDensity.value,
          }),
        )
      } catch {
        /* ignore */
      }
    },
    { deep: true },
  )

  return {
    pageDensity,
    topDensity,
    middleDensity,
    bottomDensity,
    topProxy,
    midProxy,
    botProxy,
    densityStyle,
    colW,
    allSynced,
    reset,
    syncToPage,
  }
}