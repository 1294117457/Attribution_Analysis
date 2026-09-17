<template>
  <el-card class="page-wrapper" shadow="never">
    <div class="top-area">
      <div class="top-area__header">
        <div class="top-area__title">
          <slot name="title" />
        </div>
        <div v-if="$slots.actions" class="top-area__actions">
          <slot name="actions" />
        </div>
      </div>
      <div v-if="$slots.toolbar" class="top-area__toolbar">
        <slot name="toolbar" />
      </div>
    </div>

    <div class="middle-area" :class="{ 'middle-area--full': !$slots.bottom }">
      <slot />
    </div>

    <div v-if="$slots.bottom" class="bottom-area">
      <slot name="bottom" />
    </div>
  </el-card>
</template>

<style scoped>
.page-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  --el-card-border-radius: 12px;
}

.page-wrapper :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: 20px;
  gap: 16px;
  overflow: hidden;
}

.top-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-shrink: 0;
}

.top-area__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 32px;
}

.top-area__title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.top-area__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.top-area__toolbar {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.middle-area {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.bottom-area {
  flex-shrink: 0;
  padding-top: 12px;
  border-top: 1px solid var(--color-admin-border);
}
</style>
