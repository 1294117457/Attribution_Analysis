<!-- CollectCardRow — CollectCard 内的一行：左标签 + 右控件 -->
<template>
  <div class="card-row">
    <span class="card-row__label">{{ label }}</span>
    <div class="card-row__content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string }>()
</script>

<style scoped>
.card-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  align-items: center;
  min-height: 28px;
}

.card-row__label {
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
}

.card-row__content {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 16px;
  min-width: 0;
}
</style>
