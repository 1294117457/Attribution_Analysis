<template>
  <div class="admin-page flex flex-col gap-5 h-full">
    <div class="flex items-center justify-between">
      <h2 class="page-title">📊 操作池</h2>
      <div class="flex gap-2">
        <el-input
          v-model="searchQuery"
          placeholder="搜索池名"
          clearable
          style="width: 200px"
          :prefix-icon="Search"
          @input="onSearchInput"
        />
        <el-button type="primary" @click="showCreateDialog">
          <el-icon class="mr-1"><Plus /></el-icon>
          新建池
        </el-button>
      </div>
    </div>

    <!-- 池卡片列表 -->
    <div v-loading="store.loading" class="flex-1 overflow-auto">
      <div v-if="filteredPools.length === 0 && !store.loading" class="empty-state">
        <el-empty description="还没有操作池，点击右上角新建">
          <el-button type="primary" @click="showCreateDialog">新建第一个池</el-button>
        </el-empty>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <el-card
          v-for="pool in filteredPools"
          :key="pool.id"
          shadow="hover"
          class="pool-card cursor-pointer transition-all hover:-translate-y-1"
          :class="{ 'is-default': pool.is_default }"
          @click="goToPool(pool)"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="flex items-center gap-2 flex-1 min-w-0">
              <span v-if="pool.icon" class="text-2xl">{{ pool.icon }}</span>
              <span v-else-if="pool.color" class="icon-fallback" :style="{ background: pool.color }">
                {{ pool.name.charAt(0) }}
              </span>
              <span class="text-base font-semibold truncate">{{ pool.name }}</span>
            </div>
            <el-tag v-if="pool.is_default" type="warning" size="small">默认</el-tag>
            <el-dropdown trigger="click" @click.stop @command="(c: string) => onCardMenu(c, pool)">
              <el-button text size="small" @click.stop>
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">重命名</el-dropdown-item>
                  <el-dropdown-item command="edit">编辑</el-dropdown-item>
                  <el-dropdown-item v-if="!pool.is_default" command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <div class="text-xs text-gray-500 mb-2 truncate min-h-[20px]">
            {{ pool.description || '—' }}
          </div>

          <div class="flex items-center justify-between text-xs text-gray-400">
            <span>
              <el-icon class="mr-1"><DataLine /></el-icon>
              {{ pool.member_count }} 只股票
            </span>
            <span>{{ formatDate(pool.updated_at) }}</span>
          </div>

          <div class="flex items-center gap-2 mt-3">
            <el-tag
              :type="poolTypeTag(pool.pool_type) as 'primary' | 'success' | 'warning' | 'info'"
              size="small"
              effect="plain"
            >
              {{ poolTypeLabel(pool.pool_type) }}
            </el-tag>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 创建/编辑池弹窗 -->
    <PoolCreateDialog
      v-model="createDialogVisible"
      :pool="editingPool"
      @saved="onPoolSaved"
    />

    <!-- 删除确认 -->
    <el-dialog v-model="deleteDialogVisible" title="删除确认" width="400px">
      <p>确定删除池「{{ deletingPool?.name }}」吗？所有成员关联将被移除，操作记录保留。</p>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmDelete">确定删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Plus, MoreFilled, DataLine } from '@element-plus/icons-vue'
import { usePoolStore } from '@/stores/pool'
import type { Pool } from '@/views/stock-pool/api'
import PoolCreateDialog from '@/views/stock-pool/popup/PoolCreateDialog.vue'

const router = useRouter()
const store = usePoolStore()

// ── 搜索 ─────────────────────────────────────────────────────────────
const searchQuery = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {}, 300)
}

const filteredPools = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return store.pools
  return store.pools.filter(
    (p) =>
      p.name.toLowerCase().includes(q) ||
      (p.description ?? '').toLowerCase().includes(q),
  )
})

// ── 路由跳转 ─────────────────────────────────────────────────────────
function goToPool(pool: Pool) {
  router.push({ path: `/home/pool/${pool.id}` })
}

// ── 卡片菜单 ─────────────────────────────────────────────────────────
const createDialogVisible = ref(false)
const editingPool = ref<Pool | null>(null)
const deleteDialogVisible = ref(false)
const deletingPool = ref<Pool | null>(null)

function showCreateDialog() {
  editingPool.value = null
  createDialogVisible.value = true
}

function onCardMenu(command: string, pool: Pool) {
  if (command === 'edit' || command === 'rename') {
    editingPool.value = pool
    createDialogVisible.value = true
  } else if (command === 'delete') {
    deletingPool.value = pool
    deleteDialogVisible.value = true
  }
}

async function confirmDelete() {
  if (!deletingPool.value) return
  try {
    await store.deletePool(deletingPool.value.id)
    ElMessage.success('删除成功')
    deleteDialogVisible.value = false
  } catch (e) {
    ElMessage.error('删除失败: ' + (e as Error).message)
  }
}

async function onPoolSaved(pool: Pool) {
  // 池已保存，store 已更新；不需要再 fetchPools
  ElMessage.success('保存成功')
}

// ── 显示辅助 ─────────────────────────────────────────────────────────
function formatDate(v?: string | null) {
  if (!v) return ''
  const d = new Date(v)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function poolTypeLabel(type: string) {
  const map: Record<string, string> = {
    watchlist: '自选',
    industry: '行业',
    strategy: '策略',
    custom: '自定义',
  }
  return map[type] || type
}

function poolTypeTag(type: string) {
  const map: Record<string, string> = {
    watchlist: 'warning',
    industry: 'success',
    strategy: 'primary',
    custom: 'info',
  }
  return map[type] || 'info'
}

// ── 生命周期 ─────────────────────────────────────────────────────────
onMounted(() => {
  store.fetchPools()
})
</script>

<style scoped>
.admin-page {
  min-height: 100%;
}

.pool-card {
  border-radius: 8px;
  transition: all 0.2s ease;
}

.pool-card.is-default {
  border-color: #FFB800;
}

.icon-fallback {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
</style>
