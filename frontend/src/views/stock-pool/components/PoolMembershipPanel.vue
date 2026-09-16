<!-- 所在操作池面板 -->
<template>
  <div class="pool-panel">
    <el-table
      v-if="pools.length"
      :data="pools"
      stripe
      size="small"
    >
      <el-table-column prop="pool_name" label="池名称" />
      <el-table-column prop="joined_at" label="加入时间" width="120">
        <template #default="{ row }">
          {{ row.joined_at ?? '—' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            size="small"
            @click="goPool(row.pool_id)"
          >
            查看
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-else description="该股票不在任何操作池中" />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { PoolMembership } from '@/views/stock-info/api'

defineProps<{ pools: PoolMembership[] }>()

const router = useRouter()
function goPool(poolId: number) {
  router.push(`/home/pool/${poolId}`)
}
</script>