<!--
 * components/ConceptTag.vue
 *
 * 单个概念 Tag，带 hover/click 反馈、tooltip、按 concept_type 染色。
 * 配套设计文档：docs/dev/06gainian/04-frontend-detail-design.md §2.4.1
 -->
<template>
  <el-tooltip
    :content="concept.description || '点击查看概念详情'"
    placement="top"
    :show-after="200"
  >
    <el-tag
      :type="tagType"
      :effect="hovered ? 'dark' : 'plain'"
      round
      class="concept-tag"
      :class="{ 'is-clickable': true }"
      @mouseenter="hovered = true"
      @mouseleave="hovered = false"
      @click.stop="$emit('click', concept)"
    >
      <el-icon v-if="iconForType" class="mr-1"><component :is="iconForType" /></el-icon>
      {{ concept.name }}
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
} from '@element-plus/icons-vue'
import type { ConceptGroupedVO, ConceptType } from '@/views/stock-info/api'

const props = defineProps<{ concept: ConceptGroupedVO }>()
defineEmits<{ click: [c: ConceptGroupedVO] }>()

const hovered = ref(false)

const tagType = computed(() => {
  const map: Record<ConceptType, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    industry: 'primary',
    theme:    'success',
    style:    'warning',
    region:   'info',
    event:    'danger',
    other:    'info',
  }
  return map[props.concept.concept_type] || 'info'
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
  return map[props.concept.concept_type]
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
</style>
