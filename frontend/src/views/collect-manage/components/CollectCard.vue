<!--
  CollectCard — 采集管理右侧操作卡片外壳（采集 / 试查共用）

  ┌ title [tags] description（一行，超出省略，悬浮显示全文） ┐
  ├ 默认插槽：若干 CollectCardRow（标签 + 控件）            ┤
  └ #footer：右对齐的操作区（并发度 / 主按钮）               ┘
-->
<template>
  <section class="collect-card">
    <header class="collect-card__head">
      <h3 class="collect-card__title">{{ title }}</h3>
      <slot name="tags" />
      <el-tooltip
        v-if="description"
        :content="description"
        placement="bottom-start"
        :show-after="300"
      >
        <span class="collect-card__desc">{{ description }}</span>
      </el-tooltip>
    </header>
    <div class="collect-card__body">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="collect-card__foot">
      <slot name="footer" />
    </footer>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<style scoped>
.collect-card {
  flex-shrink: 0;
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.collect-card__head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 10px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.collect-card__title {
  flex-shrink: 0;
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.collect-card__desc {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #64748b;
}

.collect-card__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 16px;
}

.collect-card__foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 16px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  border-radius: 0 0 8px 8px;
}
</style>
