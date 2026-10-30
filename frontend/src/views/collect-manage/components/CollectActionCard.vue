<!--
  CollectActionCard.vue — 采集卡片分发器（按 strategy 渲染三种不同形态）

  ★ 契约（见 backend-java/docs/开发文档/采集模块/采集模块重构开发文档.md §7.2）：
    旧版这里渲染 16 种参数控件 + 「全量/条件」单选，本版彻底废弃。
    现在按 service 声明的 strategy 分发到三种**形态完全不同**的卡片：

      strategy='incremental' → IncrementalCollectCard（只有时间范围 + 一个按钮）
      strategy='full'        → FullCollectCard（只有一个按钮 + 二次确认）
      strategy='realtime'    → RealtimePanel（占位，无采集入口）

  ⚠️ 旧版把「全量/条件」做成前端单选，导致同一个 service 能在两种语义之间切换
    —— 后端无法判断写入语义、审计日志也记不清采集方式。现在采集方式由
    collector 的 service 声明**唯一决定**，前端只负责选对形态。
-->
<template>
  <IncrementalCollectCard
    v-if="strategy === 'incremental'"
    :service-name="serviceName"
    :item="item"
    :starting="starting"
    @start="(p) => emit('start', p)"
  />

  <FullCollectCard
    v-else-if="strategy === 'full'"
    :service-name="serviceName"
    :item="item"
    :starting="starting"
    @start="(p) => emit('start', p)"
  />

  <!-- strategy='realtime' 由 CollectTaskPane 直接走 RealtimePanel，这里兜底 -->
  <el-empty v-else description="未知采集方式" />
</template>

<script setup lang="ts">
import { computed } from 'vue'

import IncrementalCollectCard from './IncrementalCollectCard.vue'
import FullCollectCard from './FullCollectCard.vue'
import type { CatalogItem, CollectStartPayload, CollectStrategy } from '../api'

const props = defineProps<{
  serviceName: string
  item: CatalogItem
  starting?: boolean
}>()

const emit = defineEmits<{
  (e: 'start', payload: CollectStartPayload): void
}>()

/** 采集方式（由 catalog 派生，已做灰度回退） */
const strategy = computed<CollectStrategy>(() => props.item.strategy)
</script>
