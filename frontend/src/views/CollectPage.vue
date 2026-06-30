<template>
  <div class="collect-page">
    <h2>数据采集</h2>

    <div class="card">
      <div class="form-group">
        <label>股票代码</label>
        <input
          v-model="symbol"
          type="text"
          placeholder="如 000001"
          @keyup.enter="handleCollect"
        />
      </div>

      <div class="form-group">
        <label>采集天数</label>
        <input v-model.number="days" type="number" min="1" max="3650" />
      </div>

      <div class="form-actions">
        <button @click="handleCollect" :disabled="loading || !symbol">
          {{ loading ? '采集中...' : '开始采集' }}
        </button>
      </div>
    </div>

    <div v-if="result" class="result" :class="result.status">
      <h3>{{ result.status === 'success' ? '采集成功' : '采集失败' }}</h3>
      <p>{{ result.message }}</p>
      <p v-if="result.name">股票名称: {{ result.name }}</p>
    </div>

    <div v-if="klines.length" class="klines-preview">
      <h3>数据预览</h3>
      <table>
        <thead>
          <tr>
            <th>日期</th>
            <th>开盘</th>
            <th>最高</th>
            <th>最低</th>
            <th>收盘</th>
            <th>涨跌幅</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="k in klines.slice(0, 10)" :key="k.id">
            <td>{{ k.date }}</td>
            <td>{{ k.open.toFixed(2) }}</td>
            <td>{{ k.high.toFixed(2) }}</td>
            <td>{{ k.low.toFixed(2) }}</td>
            <td>{{ k.close.toFixed(2) }}</td>
            <td :class="{ positive: k.change_pct > 0, negative: k.change_pct < 0 }">
              {{ k.change_pct ? k.change_pct.toFixed(2) + '%' : '-' }}
            </td>
          </tr>
        </tbody>
      </table>
      <p class="hint">共 {{ klines.length }} 条数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { stockApi } from '../api/stock'

const symbol = ref('')
const days = ref(365)
const loading = ref(false)
const result = ref(null)
const klines = ref([])

async function handleCollect() {
  if (!symbol.value) return

  loading.value = true
  result.value = null
  klines.value = []

  try {
    const res = await stockApi.collect(symbol.value, days.value)
    result.value = res.data

    if (res.data.status === 'success' && res.data.count > 0) {
      const klinesRes = await stockApi.getKlines(symbol.value, { limit: 10 })
      klines.value = klinesRes.data.items
    }
  } catch (err) {
    result.value = {
      status: 'failed',
      message: err.response?.data?.detail || err.message || '采集失败',
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.collect-page h2 {
  margin-bottom: 1.5rem;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-actions {
  margin-top: 1.5rem;
}

button {
  padding: 0.7rem 2rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
}

button:hover:not(:disabled) {
  background: #2980b9;
}

button:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.result {
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.result.success {
  background: #d4edda;
  color: #155724;
}

.result.failed {
  background: #f8d7da;
  color: #721c24;
}

.result h3 {
  margin-bottom: 0.5rem;
}

.klines-preview h3 {
  margin-bottom: 1rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

th,
td {
  padding: 0.75rem;
  text-align: right;
  border-bottom: 1px solid #eee;
}

th {
  background: #f8f9fa;
  font-weight: 500;
  text-align: right;
}

.positive {
  color: #e74c3c;
}

.negative {
  color: #27ae60;
}

.hint {
  margin-top: 0.5rem;
  color: #666;
  font-size: 0.9rem;
}
</style>
