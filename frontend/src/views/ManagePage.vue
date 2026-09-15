<template>
  <div class="manage-page">
    <div class="page-header">
      <h2>数据管理</h2>
      <div class="header-actions">
        <button @click="loadStocks" :disabled="loading" class="btn-refresh">
          {{ loading ? '加载中…' : '🔄 刷新' }}
        </button>
        <router-link to="/" class="btn-collect">+ 去采集</router-link>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stocks.length }}</div>
        <div class="stat-label">股票数量</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ totalRecords.toLocaleString() }}</div>
        <div class="stat-label">K 线总条数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ dataRange }}</div>
        <div class="stat-label">数据覆盖</div>
      </div>
    </div>

    <!-- 股票列表 -->
    <div class="card">
      <div v-if="stocks.length" class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>行业</th>
              <th>K 线条数</th>
              <th>起始日期</th>
              <th>截止日期</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in stocks" :key="s.symbol">
              <td class="symbol">{{ s.symbol }}</td>
              <td>{{ s.name || '—' }}</td>
              <td>{{ s.industry || '—' }}</td>
              <td>{{ s.record_count?.toLocaleString() ?? '—' }}</td>
              <td>{{ s.kline_start || '—' }}</td>
              <td>{{ s.kline_end || '—' }}</td>
              <td class="actions">
                <button @click="viewKlines(s)" class="btn-view">📊 查看</button>
                <button @click="handleDeleteStock(s.symbol)" class="btn-del">🗑 删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty">
        <p>暂无数据</p>
        <router-link to="/" class="btn-collect">去采集 →</router-link>
      </div>
    </div>

    <!-- K 线弹窗 -->
    <div v-if="modal.visible" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h3>{{ modal.symbol }} {{ modal.name }}</h3>
            <div class="modal-sub">K 线详情 · {{ modal.klines.length }} 条</div>
          </div>
          <button @click="closeModal" class="btn-close">×</button>
        </div>

        <!-- 统计栏 -->
        <div v-if="modal.stats" class="modal-stats">
          <span>最高: <strong>{{ modal.stats.latest_close }}</strong></span>
          <span>最新成交量: <strong>{{ modal.stats.latest_volume?.toLocaleString() }} 手</strong></span>
          <span>共 <strong>{{ modal.stats.count }}</strong> 条</span>
        </div>

        <div class="modal-body">
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>日期</th>
                  <th>开盘</th>
                  <th>最高</th>
                  <th>最低</th>
                  <th>收盘</th>
                  <th>成交量</th>
                  <th>成交额</th>
                  <th>涨跌幅</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="k in modal.klines" :key="k.date">
                  <td class="date">{{ k.date }}</td>
                  <td>{{ k.open.toFixed(2) }}</td>
                  <td>{{ k.high.toFixed(2) }}</td>
                  <td>{{ k.low.toFixed(2) }}</td>
                  <td>{{ k.close.toFixed(2) }}</td>
                  <td>{{ k.volume?.toLocaleString() }}</td>
                  <td>{{ formatAmount(k.amount) }}</td>
                  <td :class="pctClass(k.change_pct)">
                    {{ k.change_pct != null ? k.change_pct.toFixed(2) + '%' : '—' }}
                  </td>
                  <td>
                    <button @click="deleteKline(k)" class="btn-del-mini">×</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import stockApi from '../api/stock'

const loading = ref(false)
const stocks = ref([])
const modal = ref({ visible: false, symbol: '', name: '', klines: [], stats: null })

const totalRecords = computed(() =>
  stocks.value.reduce((s, x) => s + (x.record_count || 0), 0)
)

const dataRange = computed(() => {
  if (!stocks.value.length) return '—'
  const dates = stocks.value.flatMap((s) => [s.kline_start, s.kline_end]).filter(Boolean)
  if (!dates.length) return '—'
  return `${Math.min(...dates)} ~ ${Math.max(...dates)}`
})

onMounted(loadStocks)

async function loadStocks() {
  loading.value = true
  try {
    const data = await stockApi.listStocks()
    stocks.value = data.items || []
  } catch (err) {
    alert('加载失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

async function viewKlines(stock) {
  try {
    const [klinesData, statsData] = await Promise.all([
      stockApi.getKlines(stock.symbol, { limit: 200 }),
      stockApi.getKlineStats(stock.symbol),
    ])
    modal.value = {
      visible: true,
      symbol: stock.symbol,
      name: stock.name,
      klines: klinesData.items || [],
      stats: statsData,
    }
  } catch (err) {
    alert('加载 K 线失败: ' + err.message)
  }
}

function closeModal() {
  modal.value.visible = false
}

async function handleDeleteStock(symbol) {
  if (!confirm(`⚠️ 确定删除股票 ${symbol} 的全部数据？（包括所有 K 线）`)) return
  try {
    await stockApi.deleteStock(symbol)
    alert('删除成功')
    loadStocks()
    closeModal()
  } catch (err) {
    alert('删除失败: ' + err.message)
  }
}

async function deleteKline(kline) {
  if (!confirm(`删除 ${kline.date} 的 K 线？`)) return
  try {
    await stockApi.deleteKline(modal.value.symbol, kline.date)
    // refresh modal
    const data = await stockApi.getKlines(modal.value.symbol, { limit: 200 })
    modal.value.klines = data.items || []
    loadStocks()
  } catch (err) {
    alert('删除失败: ' + err.message)
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
.manage-page { display: flex; flex-direction: column; gap: 1.5rem; }

.page-header { display: flex; justify-content: space-between; align-items: center; }
.page-header h2 { font-size: 1.3rem; }
.header-actions { display: flex; gap: 0.75rem; }

.stats-row { display: flex; gap: 1rem; }
.stat-card {
  flex: 1;
  background: white;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.stat-value { font-size: 1.6rem; font-weight: 700; color: #3498db; }
.stat-label { font-size: 0.82rem; color: #888; margin-top: 0.2rem; }

.card { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }

.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
th, td { padding: 0.6rem 0.75rem; text-align: right; white-space: nowrap; }
th { background: #f8f9fa; font-weight: 500; color: #555; position: sticky; top: 0; z-index: 1; }
td:first-child, th:first-child { text-align: left; }
tr:hover td { background: #f8f9fa; }
.symbol { font-weight: 600; color: #2c3e50; }
.pos { color: #e74c3c; }
.neg { color: #27ae60; }

.actions { display: flex; gap: 0.4rem; justify-content: flex-end; }
.btn-view { background: #2ecc71; color: white; padding: 0.25rem 0.6rem; border: none; border-radius: 4px; cursor: pointer; font-size: 0.82rem; }
.btn-del { background: #e74c3c; color: white; padding: 0.25rem 0.6rem; border: none; border-radius: 4px; cursor: pointer; font-size: 0.82rem; }
.btn-del-mini { background: #e74c3c; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 0.75rem; padding: 0.1rem 0.35rem; }
.btn-refresh { background: #3498db; color: white; border: none; border-radius: 6px; padding: 0.5rem 1rem; cursor: pointer; font-size: 0.88rem; }
.btn-collect { background: #2ecc71; color: white; border: none; border-radius: 6px; padding: 0.5rem 1rem; text-decoration: none; font-size: 0.88rem; }
.btn-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #888; padding: 0; line-height: 1; }

.empty { padding: 3rem; text-align: center; color: #999; }
.empty p { margin-bottom: 1rem; }

/* modal */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal {
  background: white;
  border-radius: 10px;
  width: 95%; max-width: 1000px;
  max-height: 88vh;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 1rem 1.25rem;
  background: #f8f9fa;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}
.modal-header h3 { margin: 0; font-size: 1.1rem; }
.modal-sub { font-size: 0.82rem; color: #888; margin-top: 0.2rem; }
.modal-stats {
  display: flex; gap: 1.5rem;
  padding: 0.6rem 1.25rem;
  background: #eef6ff;
  font-size: 0.85rem;
  flex-shrink: 0;
}
.modal-body { flex: 1; overflow: hidden; padding: 1rem 1.25rem; }
</style>
