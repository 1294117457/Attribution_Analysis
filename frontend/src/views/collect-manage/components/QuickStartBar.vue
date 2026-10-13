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
  concept_index_th: [
    { label: '增量同步', params: {} },
    { label: '全量重写', params: { full: true } },
    { label: '测试前 20 个', params: { limit: 20 } },
  ],
  // 资金面（tushare，按交易日扫全市场）
  cap_moneyflow: [
    { label: '今日', params: { days: 1 } },
    { label: '7天', params: { days: 7 } },
    { label: '30天', params: { days: 30 } },
  ],
  cap_margin_detail: [
    { label: '今日', params: { days: 1 } },
    { label: '7天', params: { days: 7 } },
  ],
  cap_top_list: [
    { label: '今日龙虎榜', params: { days: 1 } },
    { label: '近 30 天', params: { days: 30 } },
  ],
  cap_top_inst: [
    { label: '今日机构', params: { days: 1 } },
    { label: '近 30 天', params: { days: 30 } },
  ],
  cap_block_trade: [
    { label: '今日大宗', params: { days: 1 } },
    { label: '近 30 天', params: { days: 30 } },
  ],
  cap_holder_num: [
    { label: '只补缺失', params: { only_missing: true } },
    { label: '全量回填', params: { only_missing: false } },
  ],
  // 基本面深度
  fin_top10_holders: [
    { label: '只补缺失', params: { only_missing: true } },
    { label: '全量回填', params: { only_missing: false } },
  ],
  fin_top10_floatholders: [
    { label: '只补缺失', params: { only_missing: true } },
    { label: '全量回填', params: { only_missing: false } },
  ],
  base_dividend: [
    { label: '只补缺失', params: { only_missing: true } },
    { label: '全量回填', params: { only_missing: false } },
  ],
  // 基础层（tech / base）
  base_adj_factor: [
    { label: '近 1 年', params: { years: 1 } },
    { label: '近 3 年', params: { years: 3 } },
    { label: '全量', params: { full: true } },
  ],
  base_suspend: [
    { label: '今日', params: { days: 1 } },
    { label: '近 30 天', params: { days: 30 } },
  ],
  base_name_change: [
    { label: '全量拉取', params: {} },
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