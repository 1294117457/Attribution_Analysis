<!--
  FullCollectCard.vue — 全量覆盖采集卡片

  ★ 契约（见 backend-java/docs/开发文档/采集模块/采集模块重构开发文档.md §7.4）：
    全量覆盖**只暴露一个按钮**，点击后二次确认即触发采集覆盖。

  提交参数：{strategy:'full', params:{}} —— **不发**任何默认参数（service 自带默认值）。

  二次确认文案按 clear_mode 区分强度：
    clear_mode='domain' → 「将覆盖现有数据，并清除覆盖域外的残留行」（红色警示）
    clear_mode='none'  → 「将重新拉取并覆盖同键数据」（黄色警示）
-->
<template>
  <CollectCard :title="item.label" :description="item.description">
    <template #tags>
      <el-tag size="small" :type="isOverwrite ? 'danger' : 'warning'" effect="plain">
        {{ isOverwrite ? '全量覆盖' : '全量采集' }}
      </el-tag>
    </template>

    <!-- 覆盖语义说明（只读，不含任何可调参数） -->
    <CollectCardRow label="采集范围">
      <span class="hint">{{ scopeHint }}</span>
    </CollectCardRow>

    <!-- 覆盖警示 -->
    <div v-if="isOverwrite" class="warn-banner warn-banner--danger">
      <div class="warn-banner__title">⚠️ 将覆盖现有数据</div>
      <div>本操作会重新拉取全量数据并<b>覆盖</b>同键记录，同时清除覆盖域外的残留行。</div>
    </div>
    <div v-else class="warn-banner">
      <div class="warn-banner__title">⚠️ 将重新拉取并覆盖同键数据</div>
      <div>本操作会重新拉取全量数据并覆盖同键记录，<b>不会</b>删除历史数据。</div>
    </div>

    <template #footer>
      <el-button
        :type="isOverwrite ? 'danger' : 'warning'"
        size="small"
        :loading="starting"
        :disabled="starting"
        @click="confirmStart"
      >{{ isOverwrite ? '全量覆盖采集' : '全量采集' }}</el-button>
    </template>
  </CollectCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessageBox } from 'element-plus'

import CollectCard from './CollectCard.vue'
import CollectCardRow from './CollectCardRow.vue'
import type { CatalogItem, CollectStartPayload } from '../api'

const props = defineProps<{
  serviceName: string
  item: CatalogItem
  starting?: boolean
}>()

const emit = defineEmits<{
  (e: 'start', payload: CollectStartPayload): void
}>()

/** 是否「真覆盖」语义（clear_mode='domain'：会清除覆盖域外的残留行） */
const isOverwrite = computed(() => props.item.clear_mode === 'domain')

/**
 * 采集范围说明。
 *
 * ★ 全量采集没有「用户可填参数」，覆盖域由 service 自身的采集源决定
 *   （例如 stock_basic 拉全部在上市股票），前端无从预知具体范围。
 *   → 只按 clear_mode 给出语义级描述。
 */
const scopeHint = computed(() =>
  isOverwrite.value
    ? '采集源全量范围（覆盖同键数据 + 清除覆盖域外残留）'
    : '采集源全量范围（覆盖同键数据，保留历史）',
)

async function confirmStart() {
  try {
    await ElMessageBox.confirm(
      isOverwrite.value
        ? `即将对「${props.item.label}」执行【全量覆盖采集】。\n\n` +
          `· 会重新拉取全量数据并覆盖同键记录\n` +
          `· 会清除覆盖域外的残留行\n\n该操作不可撤销，是否继续？`
        : `即将对「${props.item.label}」执行【全量采集】。\n\n` +
          `· 会重新拉取全量数据并覆盖同键记录\n` +
          `· 不会删除历史数据\n\n是否继续？`,
      '确认全量采集',
      {
        type: isOverwrite.value ? 'warning' : 'info',
        confirmButtonText: '确认执行',
        cancelButtonText: '取消',
        confirmButtonClass: isOverwrite.value ? 'el-button--danger' : '',
      },
    )
  } catch {
    // 用户取消
    return
  }
  // ★ 只提交 strategy + 空 params；不发 default_params（service 自带默认值）
  emit('start', { strategy: 'full', params: {} })
}
</script>

<style scoped>
.hint {
  font-size: 12px;
  color: #94a3b8;
}

.summary {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: #475569;
}

.warn-banner {
  margin-top: 4px;
  padding: 8px 12px;
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
  font-size: 12px;
  color: #92400e;
  line-height: 1.7;
}

.warn-banner--danger {
  background: #fef2f2;
  border-left-color: #ef4444;
  color: #991b1b;
}

.warn-banner__title {
  font-weight: 600;
  margin-bottom: 2px;
}
</style>
