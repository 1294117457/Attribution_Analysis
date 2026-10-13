<!--
 * components/InfoCard.vue
 *
 * 信息卡片（规范见 docs/frontend-docs/card-guide.md）
 *
 *   ┌ 标题 [tools…]                 extra ┐  ← 标题栏（全站唯一的卡片标题样式）
 *   ├─────────────────────────────────────┤
 *   └ 内容（含 el-table 时自动无内边距）  ┘
 -->
<template>
  <div class="info-card">
    <div class="info-card__header">
      <slot name="title">
        <span class="info-card__title">{{ title }}</span>
      </slot>
      <slot name="tools" />
      <span v-if="$slots.extra" class="info-card__extra"><slot name="extra" /></span>
    </div>
    <div class="info-card__body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
}>()
</script>

<style scoped>
.info-card {
  min-width: 0;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--info-card-border);
  border-radius: var(--info-card-radius);
}

.info-card__header {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  height: var(--info-card-header-h);
  padding: 0 var(--info-card-header-pr) 0 var(--info-card-header-pl);
  font-size: var(--info-card-title-fs);
  font-weight: 700;
  color: var(--info-card-title-color);
  white-space: nowrap;
  background: var(--info-card-header-bg);
  border-bottom: 1px solid var(--info-card-header-border);
}
/* 标题栏内控件：下拉框统一压到 22px，字重恢复常规 */
.info-card__header :deep(.el-select) { font-weight: 400; }
.info-card__header :deep(.el-select__wrapper) {
  min-height: 22px;
  padding: 0 8px;
  background: #fff;
}
.info-card__header :deep(.el-select__placeholder),
.info-card__header :deep(.el-select__selected-item) {
  font-size: 11px;
  line-height: 1;
}
.info-card__header :deep(.el-select__caret) { font-size: 10px; }
.info-card__header :deep(.el-tag) { font-weight: 400; }
.info-card__header :deep(.el-link) { font-size: 11px; font-weight: 400; }

.info-card__title {
  overflow: hidden;
  text-overflow: ellipsis;
}
.info-card__extra {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  font-size: 11px;
  font-weight: 400;
  color: #64748b;
}

.info-card__body {
  min-width: 0;
  padding: var(--info-card-body-padding);
}
/* 表格自带单元格内边距，内容区不再留边，表格撑满卡片宽度 */
.info-card__body:has(.el-table) { padding: 0; }
</style>
