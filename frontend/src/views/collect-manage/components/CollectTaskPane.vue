<!--
  CollectTaskPane.vue — 采集管理右侧主区（step7 简化版）

  简化前：CollectActionCard + 大日志表 + 分页 + 进度轮询
  简化后：CollectActionCard（采集模式 + 条件 + 开始采集）+ 最近一次执行结果摘要
  ── 运行日志 / 进度轮询 / 重跑 / 取消：暂不做（占位即可）

  实时 service（kind=realtime 或 both）走 RealtimePanel；其他走 CollectActionCard。
-->
<template>
  <main class="task-pane">
    <div v-if="!item" class="tip">请从左侧选择采集任务</div>

    <RealtimePanel
      v-else-if="isRealtime"
      :service-name="serviceName"
      :item="item"
      class="task-pane__scroll"
    />

    <template v-else>
      <CollectActionCard
        :service-name="serviceName"
        :item="item"
        :starting="running"
        @start="runServiceAndWait(serviceName, $event)"
      />

      <!-- 最近一次执行结果（成功/失败 一次性返回） -->
      <div v-if="lastResult" class="result-card">
        <div class="result-card__title">
          <el-icon :color="lastResultColor" class="mr-1">
            <component :is="lastResultIcon" />
          </el-icon>
          最近一次执行结果
        </div>
        <div class="result-card__stats">
          <span class="stat"><b class="text-green-600">{{ lastResult.success ?? 0 }}</b> 成功</span>
          <span class="stat"><b class="text-red-500">{{ lastResult.fail ?? 0 }}</b> 失败</span>
          <span class="stat"><b class="text-gray-500">{{ lastResult.skip ?? 0 }}</b> 跳过</span>
          <span class="stat"><b>{{ lastResult.saved ?? 0 }}</b> 写入</span>
          <span class="stat"><b>{{ lastResult.total ?? 0 }}</b> 总数</span>
        </div>
        <div v-if="lastResult.message" class="result-card__msg">
          {{ lastResult.message }}
        </div>
        <div v-if="lastResultItems.length > 0" class="result-card__items">
          <div class="result-card__items-title">返回数据（前 5 条）</div>
          <pre class="result-card__items-body">{{ JSON.stringify(lastResultItems, null, 2) }}</pre>
        </div>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleClose, CircleCheck, InfoFilled } from '@element-plus/icons-vue'

import CollectActionCard from './CollectActionCard.vue'
import RealtimePanel from './RealtimePanel.vue'
import type { CatalogItem, CollectStartPayload } from '../api'
import { runService } from '../api'

const props = defineProps<{
  serviceName: string
  item: CatalogItem | null | undefined
}>()

/** 实时 = kind='realtime'（纯实时，不入库）
 *  - kind='collect' : 走 CollectActionCard（开始采集）
 *  - kind='both'    : 也走 CollectActionCard（开始采集 + 试查入口由 Card 自身处理）
 *  - kind='realtime': 走 RealtimePanel（只显示试查，没有开始采集按钮）
 */
const isRealtime = computed(() => props.item?.kind === 'realtime')

// ── 最近一次执行结果（本地状态，无后端持久化） ─────────────
const lastResult = ref<any>(null)
const running = ref(false)

const lastResultColor = computed(() => {
  const r = lastResult.value
  if (!r) return '#94a3b8'
  if (r.fail > 0) return '#ef4444'
  if (r.success > 0) return '#22c55e'
  return '#3b82f6'
})

const lastResultIcon = computed(() => {
  const r = lastResult.value
  if (!r) return InfoFilled
  if (r.fail > 0) return CircleClose
  return CircleCheck
})

const lastResultItems = computed<any[]>(() => {
  const items = lastResult.value?.items
  if (Array.isArray(items)) return items.slice(0, 5)
  return []
})

/** 触发一次 service.collect()（带 mode + params） */
async function runServiceAndWait(
  serviceName: string,
  payload: CollectStartPayload,
) {
  console.log('[CollectTaskPane] runService', serviceName, payload)
  running.value = true
  try {
    const res = await runService(serviceName, payload)
    lastResult.value = res
    ElMessage.success(res?.message || '采集完成')
  } catch (e: any) {
    lastResult.value = {
      success: 0,
      fail: 1,
      skip: 0,
      saved: 0,
      total: 1,
      message: e?.response?.data?.message || e?.message || '采集失败',
    }
    ElMessage.error(lastResult.value.message)
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.task-pane {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.task-pane__scroll {
  flex: 1;
  min-height: 0;
}

.tip {
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

/* ── 最近一次执行结果卡片 ── */
.result-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  flex-shrink: 0;
}

.result-card__title {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}

.result-card__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: #475569;
  margin-bottom: 8px;
}

.result-card__stats .stat b {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 14px;
  margin-right: 2px;
}

.result-card__msg {
  font-size: 12px;
  color: #64748b;
  background: #f8fafc;
  padding: 6px 10px;
  border-radius: 4px;
  border-left: 3px solid #94a3b8;
}

.result-card__items {
  margin-top: 8px;
}

.result-card__items-title {
  font-size: 12px;
  color: #475569;
  font-weight: 500;
  margin-bottom: 4px;
}

.result-card__items-body {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
  background: #0f172a;
  color: #e2e8f0;
  padding: 8px 10px;
  border-radius: 4px;
  max-height: 200px;
  overflow: auto;
  margin: 0;
}
</style>
