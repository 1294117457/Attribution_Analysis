<!--
  QuickStartBar — 当前 task_type 的快捷启动按钮组

  按 task_type 查表得到按钮定义，每个按钮触发 `start(taskType, params)`。

  - planned task 时整组置灰 + tooltip 提示
  - 保持与改造前 CollectManage.vue 内联按钮的视觉一致

  配套：docs/dev/step2/02datamanage/01-采集管理四维重构方案.md §3.2.3
-->
<template>
  <div class="quick-start-bar">
    <template v-if="buttons.length > 0">
      <el-button
        v-for="b in buttons"
        :key="b.label"
        size="small"
        :disabled="disabled || loading"
        @click="emit('start', taskType, b.params)"
      >
        {{ b.label }}
      </el-button>
    </template>
    <el-tag v-else type="info" size="small">无快捷按钮</el-tag>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface QuickButton {
  label: string
  params: Record<string, any>
}

const props = defineProps<{
  taskType: string
  disabled: boolean
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'start', taskType: string, params: Record<string, any>): void
}>()

/** 按 task_type 决定快捷启动按钮 */
const BUTTONS_BY_TASK: Record<string, QuickButton[]> = {
  // 技术面
  daily_kline: [
    { label: '今日', params: { days: 1 } },
    { label: '7天', params: { days: 7 } },
    { label: '30天', params: { days: 30 } },
  ],
  // 基本面
  daily_basic: [
    { label: '同步今日', params: { days: 1 } },
    { label: '近3天', params: { days: 3 } },
    { label: '近7天', params: { days: 7 } },
  ],
  stock_basic: [
    { label: '全量同步', params: {} },
  ],
  fin_report: [
    { label: '最近 1 年', params: { years: 1 } },
    { label: '回填 3 年', params: { years: 3 } },
    { label: '只补缺失（3 年）', params: { years: 3, only_missing: true } },
    { label: '测试前 20 只', params: { years: 1, limit: 20 } },
  ],
  concept: [
    { label: '同步清单', params: {} },
  ],
  concept_membership: [
    { label: '同步全部概念', params: {} },
    { label: '测试前 20 个', params: { limit: 20 } },
  ],
  concept_reason: [
    { label: '补全缺失理由', params: { only_missing: true } },
    { label: '全量', params: {} },
  ],
  concept_index_th: [
    { label: '增量同步', params: {} },
    { label: '全量重写', params: { full: true } },
    { label: '测试前 20 个', params: { limit: 20 } },
  ],
  concept_snapshot: [
    { label: '同步全部概念', params: {} },
    { label: '测试前 30 个', params: { limit: 30 } },
  ],
}

const buttons = computed<QuickButton[]>(
  () => BUTTONS_BY_TASK[props.taskType] || [],
)
</script>

<style scoped>
.quick-start-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
</style>