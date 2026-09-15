<template>
  <div class="collect-page">

    <!-- ── 单只采集 ───────────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">📥 单只股票采集</h2>
      <div class="card">
        <div class="form-row">
          <div class="form-group">
            <label>股票代码</label>
            <input
              v-model="symbol"
              type="text"
              maxlength="6"
              placeholder="如 000001 / 600519"
              @keyup.enter="handleCollect"
              @input="symbol = symbol.replace(/\D/g, '')"
            />
          </div>
          <div class="form-group narrow">
            <label>回溯天数</label>
            <input v-model.number="days" type="number" min="1" max="3650" />
          </div>
          <div class="form-group narrow">
            <label>&nbsp;</label>
            <button @click="handleCollect" :disabled="loading || !symbol" class="btn-primary">
              {{ loading ? '采集中…' : '开始采集' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- ── 批量采集 ───────────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">📦 批量采集</h2>
      <div class="card">
        <div class="form-group">
          <label>股票代码（逗号分隔）</label>
          <input
            v-model="batchSymbols"
            type="text"
            placeholder="600519, 000858, 300750"
          />
        </div>
        <div class="form-row">
          <div class="form-group narrow">
            <label>回溯天数</label>
            <input v-model.number="batchDays" type="number" min="1" max="3650" />
          </div>
          <div class="form-group narrow">
            <label>&nbsp;</label>
            <button @click="handleBatch" :disabled="batchLoading || !batchSymbols" class="btn-primary">
              {{ batchLoading ? '采集中…' : '批量采集' }}
            </button>
          </div>
        </div>
        <!-- 批量结果 -->
        <div v-if="batchResults.length" class="batch-results">
          <h4>采集结果</h4>
          <div class="result-grid">
            <div
              v-for="r in batchResults"
              :key="r.symbol"
              class="result-item"
              :class="r.saved_count > 0 ? 'ok' : r.total_count === 0 ? 'empty' : 'err'"
            >
              <span class="result-symbol">{{ r.symbol }}</span>
              <span class="result-name">{{ r.name || '—' }}</span>
              <span class="result-count">
                <template v-if="r.saved_count > 0">✅ {{ r.saved_count }} 条</template>
                <template v-else-if="r.total_count === 0">⚠️ 无数据</template>
                <template v-else>❌ {{ r.message }}</template>
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── 采集结果 & 预览 ───────────────────────────── -->
    <section class="section" v-if="result">
      <h2 class="section-title">📊 采集结果</h2>
      <div class="result-banner" :class="result.saved_count > 0 ? 'ok' : 'warn'">
        <div class="result-symbol-big">{{ result.symbol }}</div>
        <div class="result-meta">
          <div class="meta-item">
            <span class="meta-label">股票名称</span>
            <span class="meta-value">{{ result.name || '—' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">新增入库</span>
            <span class="meta-value">{{ result.saved_count }} 条</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">总获取</span>
            <span class="meta-value">{{ result.total_count }} 条</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">说明</span>
            <span class="meta-value">{{ result.message }}</span>
          </div>
        </div>
      </div>

      <!-- K 线预览 -->
      <div v-if="klines.length" class="card kline-table">
        <h3 class="table-title">数据预览（最近 {{ klines.length }} 条）</h3>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>开盘</th>
                <th>最高</th>
                <th>最低</th>
                <th>收盘</th>
                <th>成交量(手)</th>
                <th>成交额(元)</th>
                <th>涨跌幅</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="k in klines" :key="k.date">
                <td class="date">{{ k.date }}</td>
                <td>{{ k.open.toFixed(2) }}</td>
                <td>{{ k.high.toFixed(2) }}</td>
                <td>{{ k.low.toFixed(2) }}</td>
                <td>{{ k.close.toFixed(2) }}</td>
                <td>{{ k.volume.toLocaleString() }}</td>
                <td>{{ formatAmount(k.amount) }}</td>
                <td :class="pctClass(k.change_pct)">
                  {{ k.change_pct != null ? k.change_pct.toFixed(2) + '%' : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- ── 最近采集概览 ─────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">📋 已采集股票</h2>
      <div class="card" v-if="recentStocks.length">
        <div class="recent-grid">
          <div v-for="s in recentStocks" :key="s.symbol" class="recent-item">
            <span class="recent-symbol">{{ s.symbol }}</span>
            <span class="recent-name">{{ s.name }}</span>
            <span class="recent-count">{{ s.record_count }} 条</span>
            <span class="recent-range">{{ s.kline_start }} ~ {{ s.kline_end }}</span>
          </div>
        </div>
        <div class="recent-footer">
          <router-link to="/manage" class="btn-outline">进入管理 →</router-link>
        </div>
      </div>
      <div v-else class="card empty-card">
        <p>暂无已采集股票</p>
      </div>
    </section>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import stockApi from '../api/stock'

// ── 单只采集 ──────────────────────────────────────────────
const symbol = ref('')
const days = ref(365)
const loading = ref(false)
const result = ref(null)
const klines = ref([])

// ── 批量采集 ──────────────────────────────────────────────
const batchSymbols = ref('600519, 000858, 300750')
const batchDays = ref(60)
const batchLoading = ref(false)
const batchResults = ref([])

// ── 已采集列表 ────────────────────────────────────────────
const recentStocks = ref([])

onMounted(() => {
  loadRecent()
})

async function loadRecent() {
  try {
    const data = await stockApi.listStocks()
    recentStocks.value = (data.items || []).slice(0, 10)
  } catch (_) {}
}

async function handleCollect() {
  if (!symbol.value) return
  loading.value = true
  result.value = null
  klines.value = []
  try {
    result.value = await stockApi.collectKlines({
      symbol: symbol.value.trim(),
      days: days.value,
    })
    if (result.value.saved_count > 0) {
      const data = await stockApi.getKlines(symbol.value.trim(), { limit: 10 })
      klines.value = (data.items || []).reverse()
    }
    loadRecent()
  } catch (err) {
    alert(err.message)
  } finally {
    loading.value = false
  }
}

async function handleBatch() {
  const raw = batchSymbols.value.replace(/\s/g, '')
  const symbols = raw.split(',').filter((s) => s.length === 6)
  if (!symbols.length) {
    alert('请输入有效的 6 位股票代码')
    return
  }
  batchLoading.value = true
  batchResults.value = []
  try {
    const data = await stockApi.collectBatch(symbols, batchDays.value)
    batchResults.value = Object.values(data).map((v) => ({
      symbol: v.symbol,
      name: v.name,
      saved_count: v.saved_count,
      total_count: v.total_count,
      message: v.message,
    }))
    loadRecent()
  } catch (err) {
    alert(err.message)
  } finally {
    batchLoading.value = false
  }
}

function formatAmount(v) {
  if (v == null) return '—'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + ' 亿'
  if (v >= 1e4) return (v / 1e4).toFixed(2) + ' 万'
  return v.toFixed(2)
}

function pctClass(pct) {
  if (pct == null) return ''
  return pct > 0 ? 'pos' : pct < 0 ? 'neg' : ''
}
</script>

<style scoped>
.collect-page { display: flex; flex-direction: column; gap: 2rem; }

.section-title {
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
  color: #2c3e50;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 1.25rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.form-row { display: flex; gap: 1rem; align-items: flex-end; flex-wrap: wrap; }

.form-group { display: flex; flex-direction: column; flex: 1; min-width: 140px; }
.form-group.narrow { flex: 0 0 auto; min-width: 100px; }

.form-group label { font-size: 0.85rem; color: #666; margin-bottom: 0.3rem; font-weight: 500; }
.form-group input {
  padding: 0.55rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
}
.form-group input:focus { outline: none; border-color: #3498db; box-shadow: 0 0 0 2px rgba(52,152,219,0.15); }

.btn-primary {
  padding: 0.55rem 1.25rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  cursor: pointer;
  white-space: nowrap;
}
.btn-primary:hover:not(:disabled) { background: #2980b9; }
.btn-primary:disabled { background: #bdc3c7; cursor: not-allowed; }

.btn-outline {
  display: inline-block;
  padding: 0.5rem 1rem;
  border: 1px solid #3498db;
  color: #3498db;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.9rem;
}
.btn-outline:hover { background: #3498db; color: white; }

/* batch results */
.batch-results { margin-top: 1rem; }
.batch-results h4 { font-size: 0.9rem; color: #666; margin-bottom: 0.5rem; }
.result-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.result-item {
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #f8f9fa;
}
.result-item.ok { background: #d4edda; color: #155724; }
.result-item.empty { background: #fff3cd; color: #856404; }
.result-item.err { background: #f8d7da; color: #721c24; }
.result-symbol { font-weight: 600; }
.result-name { color: inherit; opacity: 0.8; }
.result-count { font-size: 0.8rem; }

/* result banner */
.result-banner {
  border-radius: 8px;
  padding: 1rem 1.25rem;
  display: flex;
  gap: 2rem;
  align-items: center;
  margin-bottom: 1rem;
}
.result-banner.ok { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
.result-banner.warn { background: #fff3cd; border: 1px solid #ffeeba; color: #856404; }
.result-symbol-big { font-size: 1.8rem; font-weight: 700; }
.result-meta { display: flex; flex-wrap: wrap; gap: 1rem 2rem; }
.meta-item { display: flex; flex-direction: column; }
.meta-label { font-size: 0.78rem; opacity: 0.7; }
.meta-value { font-size: 0.95rem; font-weight: 500; }

/* kline table */
.kline-table { padding: 1rem 1.25rem; }
.table-title { font-size: 0.95rem; margin-bottom: 0.75rem; color: #555; }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
th, td { padding: 0.5rem 0.75rem; text-align: right; white-space: nowrap; }
th { background: #f8f9fa; font-weight: 500; color: #555; position: sticky; top: 0; }
td:first-child, th:first-child { text-align: left; }
tr:hover td { background: #f8f9fa; }
.date { color: #555; font-size: 0.85rem; }
.pos { color: #e74c3c; }
.neg { color: #27ae60; }

/* recent stocks */
.recent-grid { display: flex; flex-direction: column; gap: 0.5rem; }
.recent-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 0.88rem;
}
.recent-symbol { font-weight: 600; min-width: 64px; }
.recent-name { flex: 1; }
.recent-count { color: #3498db; font-weight: 500; min-width: 60px; text-align: right; }
.recent-range { color: #999; font-size: 0.8rem; }
.recent-footer { margin-top: 0.75rem; text-align: right; }

.empty-card { text-align: center; color: #999; padding: 2rem; }
</style>
