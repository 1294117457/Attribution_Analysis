<template>
  <el-dialog
    :model-value="modelValue"
    :title="`将 ${stocks.length} 只股票加入操作池`"
    width="520px"
    @update:model-value="$emit('update:modelValue', $event)"
    @close="resetState"
  >
    <div v-if="isCreating" class="space-y-3">
      <el-form label-width="80px">
        <el-form-item label="池名称" required>
          <el-input
            v-model="newPoolName"
            placeholder="如：银行股组合"
            maxlength="64"
            clearable
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="newPoolType" style="width: 100%">
            <el-option label="⭐ 自选股" value="watchlist" />
            <el-option label="🏦 行业" value="industry" />
            <el-option label="📈 策略" value="strategy" />
            <el-option label="📂 自定义" value="custom" />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <div v-else class="space-y-3">
      <p class="text-sm text-gray-600">
        选中 <strong>{{ stocks.length }}</strong> 只股票：
        <span class="mono">{{ stocks.map(s => s.symbol).slice(0, 10).join(', ') }}{{ stocks.length > 10 ? '...' : '' }}</span>
      </p>

      <el-form label-width="80px">
        <el-form-item label="选择操作池" required>
          <el-select
            v-model="selectedPoolId"
            placeholder="请选择一个操作池"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="pool in activePools"
              :key="pool.id"
              :label="`${pool.icon || '📂'} ${pool.name} (${pool.member_count}只)`"
              :value="pool.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <div class="text-xs text-gray-400 flex items-center justify-between">
        <span>
          {{ selectedPoolId ? `已选: ${getPoolName(selectedPoolId)}` : '请选择操作池' }}
        </span>
        <el-button text type="primary" size="small" @click="isCreating = true">
          + 新建池
        </el-button>
      </div>
    </div>

    <template #footer>
      <div class="flex gap-2">
        <el-button @click="$emit('update:modelValue', false)">取消</el-button>
        <el-button
          v-if="isCreating"
          text
          type="primary"
          @click="isCreating = false; selectedPoolId = null"
        >
          返回选择池
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="!canSubmit"
          class="flex-1"
          @click="handleSubmit"
        >
          {{ isCreating ? '创建并加入' : '确认加入' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePoolStore } from '@/stores/pool'
import type { StockInfo } from '@/views/stock-info/api'

const props = defineProps<{
  modelValue: boolean
  stocks: StockInfo[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  done: []
}>()

const router = useRouter()
const poolStore = usePoolStore()

const isCreating = ref(false)
const selectedPoolId = ref<number | null>(null)
const newPoolName = ref('')
const newPoolType = ref<'watchlist' | 'industry' | 'strategy' | 'custom'>('custom')
const submitting = ref(false)

const activePools = computed(() =>
  poolStore.pools.filter((p) => !p.is_archived)
)

const canSubmit = computed(() => {
  if (isCreating.value) return newPoolName.value.trim().length > 0
  return selectedPoolId.value !== null
})

function getPoolName(poolId: number): string {
  return poolStore.pools.find((p) => p.id === poolId)?.name ?? ''
}

function resetState() {
  isCreating.value = false
  newPoolName.value = ''
  newPoolType.value = 'custom'
  selectedPoolId.value = null
}

async function handleSubmit() {
  if (!canSubmit.value) return

  submitting.value = true
  try {
    const symbols = props.stocks.map((s) => s.symbol)
    let targetPoolId: number

    if (isCreating.value) {
      const newPool = await poolStore.createPool({
        name: newPoolName.value.trim(),
        pool_type: newPoolType.value,
      })
      targetPoolId = typeof newPool.id === 'number' ? newPool.id : NaN
    } else {
      targetPoolId = typeof selectedPoolId.value === 'number'
        ? selectedPoolId.value
        : NaN
    }

    if (Number.isNaN(targetPoolId)) {
      ElMessage.error('池 ID 无效')
      submitting.value = false
      return
    }

    const result = await poolStore.addMembers(targetPoolId, symbols)
    ElMessage.success(
      `已成功添加 ${result.total_added} 只，跳过 ${result.total_skipped} 只`
    )

    emit('update:modelValue', false)
    emit('done')

    const targetPool = poolStore.pools.find((p) => p.id === targetPoolId)
    if (targetPool) {
      ElMessage({
        type: 'success',
        message: `已加入「${targetPool.name}」，点击跳转到操作池`,
        duration: 4000,
        onClose: () => router.push(`/home/pool/${targetPoolId}`),
      })
    }
  } catch (e) {
    ElMessage.error('加入失败: ' + (e as Error).message)
  } finally {
    submitting.value = false
  }
}
</script>
