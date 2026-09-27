<!--
 * components/ConceptTag.vue
 *
 * 单个概念 Tag，带 hover/click 反馈、tooltip、按 concept_type 染色。
 *
 * 配套设计文档：docs/dev/06gainian/04-frontend-detail-design.md §2.4.1
 *               docs/dev/08concept/04-frontend-stockinfo.md §四
 *               docs/dev/09concept/04-frontend-stockinfo.md §概念 Tag 涨跌染色
 *
 * 08concept 增量：
 * - 支持双类型入参（ConceptMainVO / ConceptGroupedVO / 合并后的 dict）
 * - tooltip 优先级：reason（实时） > description（DB） > 默认文案
 * - is_realtime=true 时显示 ⚡ 标识
 *
 * 09concept 增量：
 * - 支持 snapshot 字段，根据 pct_change 给 Tag 后缀加红/绿/灰数字
 * - 涨染色规则：pct_change > 0 红，< 0 绿，= 0 灰（同花顺配色）
-->
<template>
  <el-tooltip
    :content="tooltipContent"
    placement="top"
    :show-after="200"
  >
    <el-tag
      :type="tagType"
      :effect="hovered ? 'dark' : 'plain'"
      round
      class="concept-tag"
      :class="{
        'is-clickable': true,
        'is-realtime': isRealtime,
        [`color-${snapshotColor}`]: !!snapshot,
      }"
      @mouseenter="hovered = true"
      @mouseleave="hovered = false"
      @click.stop="$emit('click', concept)"
    >
      <el-icon v-if="iconForType" class="mr-1"><component :is="iconForType" /></el-icon>
      {{ concept.name }}
      <span v-if="snapshot && snapshot.pct_change !== undefined" class="pct-suffix">
        {{ formattedPctChange }}
      </span>
      <el-icon v-if="isRealtime" class="ml-1 is-realtime-icon" :size="11">
        <Lightning />
      </el-icon>
    </el-tag>
  </el-tooltip>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  OfficeBuilding,    // industry
  MagicStick,        // theme
  TrendCharts,       // style
  Location,          // region
  Bell,              // event
  QuestionFilled,    // other
  Lightning,         // is_realtime 标识
} from '@element-plus/icons-vue'
import type {
  ConceptBrief,
  ConceptGroupedVO,
  ConceptMainVO,
  ConceptSnapshot,
  ConceptType,
} from '@/views/stock-info/api'

// 🆕 双类型入参：ConceptMainVO（列表用） / ConceptGroupedVO（抽屉用） / 合并后的 dict
type ConceptLike =
  | ConceptBrief
  | ConceptMainVO
  | ConceptGroupedVO
  | (ConceptGroupedVO & {
      concept_code?: string | null
      is_realtime?: boolean
      reason?: string | null
    })

const props = defineProps<{ concept: ConceptLike }>()
defineEmits<{ click: [c: ConceptLike] }>()

const hovered = ref(false)

const conceptType = computed<ConceptType>(() => {
  const c = props.concept as any
  return (c.concept_type || 'other') as ConceptType
})

const isRealtime = computed(() => Boolean((props.concept as any).is_realtime))

const snapshot = computed<ConceptSnapshot | null>(() => {
  const c = props.concept as any
  return c.snapshot || null
})

const snapshotColor = computed<'up' | 'down' | 'flat' | ''>(() => {
  return snapshot.value?.color || ''
})

const formattedPctChange = computed(() => {
  const s = snapshot.value
  if (!s) return ''
  const v = s.pct_change
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
})

const tagType = computed(() => {
  const map: Record<ConceptType, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    industry: 'primary',
    theme:    'success',
    style:    'warning',
    region:   'info',
    event:    'danger',
    other:    'info',
  }
  return map[conceptType.value] || 'info'
})

const iconForType = computed(() => {
  const map: Record<ConceptType, unknown> = {
    industry: OfficeBuilding,
    theme:    MagicStick,
    style:    TrendCharts,
    region:   Location,
    event:    Bell,
    other:    QuestionFilled,
  }
  return map[conceptType.value]
})

const tooltipContent = computed(() => {
  const c = props.concept as any
  if (snapshot.value) {
    return `板块涨幅 ${formattedPctChange.value}\n` +
      (snapshot.value.rank_label ? `排名 ${snapshot.value.rank_label}\n` : '') +
      (snapshot.value.up_down_label ? `涨跌家数 ${snapshot.value.up_down_label}` : '')
  }
  if (c.reason) return c.reason         // 实时入选理由（最高优先级）
  if (c.description) return c.description  // DB 落库的入选理由
  return '点击查看概念详情'
})
</script>

<style scoped>
.concept-tag {
  margin: 0 4px 6px 0;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.concept-tag.is-clickable:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
/* 🆕 实时概念：左边一道亮黄边作为视觉提示 */
.concept-tag.is-realtime {
  border-left: 2px solid #facc15;
}
.is-realtime-icon {
  color: #facc15;
  vertical-align: middle;
}

/* 09concept：板块涨幅染色（同花顺配色：红涨绿跌灰平） */
.concept-tag.color-up {
  background-color: #fef2f2 !important;
  border-color: #fca5a5 !important;
  color: #dc2626 !important;
}
.concept-tag.color-up .pct-suffix {
  color: #dc2626;
  font-weight: 600;
  margin-left: 4px;
}
.concept-tag.color-down {
  background-color: #f0fdf4 !important;
  border-color: #86efac !important;
  color: #16a34a !important;
}
.concept-tag.color-down .pct-suffix {
  color: #16a34a;
  font-weight: 600;
  margin-left: 4px;
}
.concept-tag.color-flat .pct-suffix {
  color: #6b7280;
  font-weight: 500;
  margin-left: 4px;
}
.pct-suffix {
  font-size: 11px;
  font-family: 'SF Mono', Menlo, Consolas, monospace;
}
</style>
