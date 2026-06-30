<template>
  <div class="manage-page">
    <div class="header">
      <h2>数据管理</h2>
      <button @click="loadStocks" :disabled="loading" class="refresh-btn">
        {{ loading ? '加载中...' : '刷新' }}
      </button>
    </div>

    <div v-if="stocks.length" class="stats">
      <div class="stat-item">
        <span class="stat-value">{{ stocks.length }}</span>
        <span class="stat-label">股票数量</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ totalRecords }}</span>
        <span class="stat-label">数据总量</span>
      </div>
    </div>

    <div class="card">
      <table v-if="stocks.length">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>行业</th>
            <th>数据条数</th>
            <th>日期范围</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stock in stocks" :key="stock.symbol">
            <td>{{ stock.symbol }}</td>
            <td>{{ stock.name || '-' }}</td>
            <td>{{ stock.industry || '-' }}</td>
            <td>{{ stock.record_count }}</td>
            <td>{{ stock.kline_start }} ~ {{ stock.kline_end }}</td>
            <td>
              <button @click="viewData(stock)" class="view-btn">查看</button>
              <button @click="handleDelete(stock.symbol)" class="delete-btn">删除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-else class="empty">
        <p>暂无数据，请先采集股票数据</p>
        <router-link to="/" class="go-collect">去采集</router-link>
      </div>
    </div>

    <div v-if="selectedStock" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ selectedStock.symbol }} {{ selectedStock.name }}</h3>
          <button @click="closeModal" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>开盘</th>
                <th>最高</th>
                <th>最低</th>
                <th>收盘</th>
                <th>涨跌幅</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="k in klines" :key="k.id">
                <td>{{ k.date }}</td>
                <td>{{ k.open.toFixed(2) }}</td>
                <td>{{ k.high.toFixed(2) }}</td>
                <td>{{ k.low.toFixed(2) }}</td>
                <td>{{ k.close.toFixed(2) }}</td>
                <td :class="{ positive: k.change_pct > 0, negative: k.change_pct < 0 }">
                  {{ k.change_pct ? k.change_pct.toFixed(2) + '%' : '-' }}
                </td>
                <td>
                  <button @click="deleteKline(k)" class="del-single-btn">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { stockApi } from '../api/stock'

const loading = ref(false)
const stocks = ref([])
const selectedStock = ref(null)
const klines = ref([])

const totalRecords = computed(() =>
  stocks.value.reduce((sum, s) => sum + s.record_count, 0)
)

onMounted(() => {
  loadStocks()
})

async function loadStocks() {
  loading.value = true
  try {
    const res = await stockApi.listStocks()
    stocks.value = res.data.items
  } catch (err) {
    console.error('加载失败:', err)
  } finally {
    loading.value = false
  }
}

async function viewData(stock) {
  selectedStock.value = stock
  try {
    const res = await stockApi.getKlines(stock.symbol, { limit: 100 })
    klines.value = res.data.items
  } catch (err) {
    console.error('加载K线失败:', err)
    klines.value = []
  }
}

function closeModal() {
  selectedStock.value = null
  klines.value = []
}

async function handleDelete(symbol) {
  if (!confirm(`确定要删除 ${symbol} 的所有数据吗？`)) return

  try {
    await stockApi.deleteStock(symbol)
    alert('删除成功')
    loadStocks()
    closeModal()
  } catch (err) {
    alert('删除失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function deleteKline(kline) {
  if (!confirm(`确定要删除 ${kline.date} 的数据吗？`)) return

  try {
    await stockApi.deleteKline(kline.symbol, kline.date)
    alert('删除成功')
    viewData(selectedStock.value)
    loadStocks()
  } catch (err) {
    alert('删除失败: ' + (err.response?.data?.detail || err.message))
  }
}
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.stats {
  display: flex;
  gap: 2rem;
  margin-bottom: 1.5rem;
}

.stat-item {
  background: white;
  padding: 1rem 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 2rem;
  font-weight: 600;
  color: #3498db;
}

.stat-label {
  color: #666;
  font-size: 0.9rem;
}

.card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 0.75rem;
  text-align: right;
  border-bottom: 1px solid #eee;
}

th {
  background: #f8f9fa;
  font-weight: 500;
}

td:first-child, th:first-child {
  text-align: left;
}

.positive { color: #e74c3c; }
.negative { color: #27ae60; }

button {
  padding: 0.3rem 0.8rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  margin-left: 0.5rem;
}

.refresh-btn { background: #3498db; color: white; }
.view-btn { background: #2ecc71; color: white; }
.delete-btn { background: #e74c3c; color: white; }
.del-single-btn { background: #e74c3c; color: white; padding: 0.2rem 0.5rem; font-size: 0.75rem; }

.empty {
  padding: 3rem;
  text-align: center;
  color: #666;
}

.go-collect {
  display: inline-block;
  margin-top: 1rem;
  color: #3498db;
}

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 900px;
  max-height: 80vh;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid #eee;
}

.modal-header h3 { margin: 0; }

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  padding: 0;
  margin: 0;
}

.modal-body {
  padding: 1rem;
  max-height: 60vh;
  overflow-y: auto;
}
</style>
