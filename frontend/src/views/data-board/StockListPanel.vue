<!--
  数据看板 · 左侧股票列（200px 宽）
  - 顶部搜索框（symbol / 中文名 模糊）
  - 全量股票列表（按 symbol 升序）+ 当前选中高亮
  - 点击切换右侧看板展示的 symbol
-->
<template>
  <div class="stock-list-panel">
    <!-- 搜索框 -->
    <div class="slp-search">
      <el-input
        v-model="kw"
        size="small"
        placeholder="搜索 6 位代码 / 中文名"
        clearable
        @input="onSearchInput"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <div v-if="filtered.length !== items.length" class="slp-count text-xs text-gray-400 mt-1">
        {{ filtered.length }} / {{ items.length }}
      </div>
    </div>

    <!-- 加载/错误状态 -->
    <div v-if="loading" v-loading="true" class="slp-loading"></div>
    <el-empty
      v-else-if="items.length === 0"
      description="暂无股票数据"
      :image-size="60"
      class="slp-empty"
    />

    <!-- 列表（虚拟滚动） -->
    <el-scrollbar
      v-else
      ref="scrollRef"
      class="slp-scroll"
      @scroll="onScroll"
    >
      <div
        v-for="row in visibleRows"
        :key="row.symbol"
        class="slp-row"
        :class="{ 'slp-row--active': row.symbol === currentSymbol }"
        :style="{ height: ROW_H + 'px', transform: `translateY(${row.__y}px)` }"
        @click="select(row.symbol)"
      >
        <div class="slp-row__top">
          <span class="slp-row__symbol">{{ row.symbol }}</span>
          <span class="slp-row__name" :title="row.name || ''">{{ row.name || '—' }}</span>
        </div>
        <div class="slp-row__meta">
          <span v-if="row.industry" class="text-xs text-gray-500">{{ row.industry }}</span>
          <el-tag v-if="row.exchange" size="small" type="info" effect="plain">
            {{ exchangeLabel(row.exchange) }}
          </el-tag>
        </div>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { getStockListAll, type StockListItem } from './api'

const props = defineProps<{ currentSymbol: string }>()
const emit = defineEmits<{ (e: 'select', symbol: string): void }>()

// ── 数据 ──
const items = ref<StockListItem[]>([])
const loading = ref(false)
const kw = ref('')

// ── 过滤（symbol 前缀匹配或 name 包含） ──
const filtered = computed<StockListItem[]>(() => {
  const q = kw.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter(r =>
    (r.symbol && r.symbol.startsWith(q)) ||
    (r.name && r.name.toLowerCase().includes(q)),
  )
})

// ── 虚拟滚动（5000+ 行不卡顿） ──
const ROW_H = 44                  // 每行 44px
const BUFFER = 8                  // 上下各预渲染 8 行
const scrollTop = ref(0)
const viewportH = ref(600)

const visibleRows = computed<Array<StockListItem & { __y: number }>>(() => {
  const list = filtered.value
  const totalH = list.length * ROW_H
  const startIdx = Math.max(0, Math.floor(scrollTop.value / ROW_H) - BUFFER)
  const endIdx = Math.min(
    list.length,
    Math.ceil((scrollTop.value + viewportH.value) / ROW_H) + BUFFER,
  )
  const out: Array<StockListItem & { __y: number }> = []
  for (let i = startIdx; i < endIdx; i++) {
    out.push({ ...list[i], __y: i * ROW_H })
  }
  return out
})

const scrollRef = ref<{ scrollTo?: (opts: { top: number }) => void } | null>(null)

function onScroll(e: { scrollTop: number; clientHeight: number }) {
  scrollTop.value = e.scrollTop
  viewportH.value = e.clientHeight
}

// ── 切换股票 → 通知父组件 ──
function select(s: string) {
  if (s === props.currentSymbol) return
  emit('select', s)
}

// ── 当前选中自动滚到视口 ──
watch(() => props.currentSymbol, async (next) => {
  await nextTick()
  const idx = filtered.value.findIndex(r => r.symbol === next)
  if (idx < 0) return
  const target = Math.max(0, idx * ROW_H - viewportH.value / 2 + ROW_H / 2)
  scrollRef.value?.scrollTo?.({ top: target })
})

function onSearchInput() {
  // 搜索后自动滚回顶部（无需 nextTick，因为 computed 会响应）
  scrollRef.value?.scrollTo?.({ top: 0 })
}

function exchangeLabel(code: string | null): string {
  if (!code) return ''
  return ({ SSE: '沪', SZSE: '深', BSE: '北' } as Record<string, string>)[code] || code
}

// ── 加载 ──
onMounted(async () => {
  loading.value = true
  try {
    const res = await getStockListAll()
    items.value = res.items
  } catch (e) {
    console.warn('[StockListPanel] load failed', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stock-list-panel {
  display: flex; flex-direction: column;
  height: 100%; min-height: 0;
  border-right: 1px solid var(--el-border-color-lighter, #e2e8f0);
  background: #f8fafc;
}

.slp-search {
  padding: 8px 8px 6px;
  border-bottom: 1px solid var(--el-border-color-lighter, #e2e8f0);
  background: #fff;
  flex-shrink: 0;
}
.slp-count { padding: 0 4px; }

.slp-loading,
.slp-empty {
  flex: 1; min-height: 0;
  display: flex; align-items: center; justify-content: center;
}

.slp-scroll {
  flex: 1; min-height: 0;
}

.slp-row {
  padding: 6px 10px;
  cursor: pointer;
  border-bottom: 1px solid #f1f5f9;
  transition: background-color 0.12s;
  display: flex; flex-direction: column;
  justify-content: center;
  gap: 2px;
  overflow: hidden;
}
.slp-row:hover { background: #eef2ff; }
.slp-row--active {
  background: #e0e7ff !important;
  border-left: 3px solid #4f46e5;
  padding-left: 7px;
}

.slp-row__top {
  display: flex; gap: 6px; align-items: baseline;
  overflow: hidden;
}
.slp-row__symbol {
  font-family: ui-monospace, monospace;
  font-weight: 600;
  font-size: 0.85rem;
  color: #1e293b;
  flex-shrink: 0;
}
.slp-row__name {
  font-size: 0.85rem;
  color: #475569;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.slp-row__meta {
  display: flex; gap: 4px; align-items: center;
  overflow: hidden;
}
</style>