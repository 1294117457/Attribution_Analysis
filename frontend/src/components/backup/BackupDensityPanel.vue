<!--
  BackupDensityPanel · 复用密度面板（3 个 backup 页面共用）
  - 4 滑块：页面 / 顶部 / 表格 / 分页
  - 2 按钮：跟随 / 还原
  - 样式与 StockInfoList 的 density-inline 模式一致，前缀换成 bkup-
-->
<template>
  <transition name="density-inline">
    <div v-if="show" class="bkup-density-inline">
      <span class="bkup-density-inline__label">⚙️ 页面设置</span>
      <span class="bkup-density-inline__divider"></span>

      <div class="bkup-density-inline__group">
        <span>页面</span>
        <el-slider v-model="pageDensity" :min="0.7" :max="1.4" :step="0.05" :show-tooltip="false" />
        <span class="bkup-density-inline__value">{{ pageDensity.toFixed(2) }}</span>
      </div>

      <div class="bkup-density-inline__group">
        <span>顶部</span>
        <el-slider v-model="topProxy" :min="0.6" :max="1.5" :step="0.05" :show-tooltip="false" />
        <span class="bkup-density-inline__value">{{ topProxy.toFixed(2) }}</span>
      </div>

      <div class="bkup-density-inline__group">
        <span>表格</span>
        <el-slider v-model="midProxy" :min="0.7" :max="1.4" :step="0.05" :show-tooltip="false" />
        <span class="bkup-density-inline__value">{{ midProxy.toFixed(2) }}</span>
      </div>

      <div class="bkup-density-inline__group">
        <span>分页</span>
        <el-slider v-model="botProxy" :min="0.7" :max="1.4" :step="0.05" :show-tooltip="false" />
        <span class="bkup-density-inline__value">{{ botProxy.toFixed(2) }}</span>
      </div>

      <el-button size="small" :disabled="allSynced" @click="syncToPage">跟随</el-button>
      <el-button size="small" type="primary" :disabled="pageDensity === 1 && allSynced" @click="reset">
        还原
      </el-button>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { useBackupDensity } from '@/composables/useBackupDensity'

defineProps<{ show: boolean }>()

const {
  pageDensity,
  topProxy,
  midProxy,
  botProxy,
  allSynced,
  reset,
  syncToPage,
} = useBackupDensity()
</script>

<style scoped>
/* 与 StockInfoList 的 density-inline 样式一致；前缀 sil- → bkup- */
.bkup-density-inline {
  height: 2rem;
  max-height: 2rem;
  display: flex;
  align-items: center;
  align-self: center;
  width: auto;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  white-space: nowrap;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-radius: 0.5rem;
  padding: 0 0.5rem;
  margin-left: 0.5rem;
  box-shadow: 0 1px 3px rgba(59, 130, 246, 0.08);
}

.bkup-density-inline__label {
  font-weight: 600;
  white-space: nowrap;
  color: #1e40af;
  flex-shrink: 0;
}

.bkup-density-inline__divider {
  width: 1px;
  height: 1rem;
  background: #93c5fd;
  margin: 0 0.5rem;
  flex-shrink: 0;
}

.bkup-density-inline__group {
  display: inline-flex;
  align-items: center;
  gap: 0.357rem;
  white-space: nowrap;
  color: #475569;
  flex-shrink: 0;
}

.bkup-density-inline__value {
  display: inline-block;
  min-width: 2.25rem;
  text-align: center;
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-weight: 600;
  font-size: 0.78rem;
}

.bkup-density-inline :deep(.el-slider) {
  width: 60px;
  height: 16px;
  margin: 0;
}
.bkup-density-inline :deep(.el-slider__runway),
.bkup-density-inline :deep(.el-slider__bar) {
  height: 4px;
}
.bkup-density-inline :deep(.el-slider__button) {
  width: 12px;
  height: 12px;
}
.bkup-density-inline :deep(.el-button) {
  height: 22px;
  padding: 0 10px;
  font-size: 0.78rem;
  margin: 0 0 0 0.5rem;
}
.bkup-density-inline :deep(.el-button .el-icon) {
  font-size: 0.78rem;
}

.density-inline-enter-active,
.density-inline-leave-active {
  transition: opacity 0.22s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}
.density-inline-enter-from,
.density-inline-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}
</style>