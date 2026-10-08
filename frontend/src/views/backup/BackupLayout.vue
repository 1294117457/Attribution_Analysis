<!--
  BackupLayout · 父布局
  - 标题栏：图标 + 标题 + 路径配置按钮
  - ⚙️ 密度面板按钮 + 复用密度面板
  - Tab 切换：创建备份 / 备份历史
  - router-view 子页面
  - 路径配置弹窗
-->
<template>
  <PageWrapper :style="densityStyle" class="bkup-page">
    <template #title>
      <el-icon class="bkup-title-icon"><FolderOpened /></el-icon>
      <span class="bkup-page-title">数据备份</span>

      <BackupDensityPanel :show="showDensity" />

      <button
        class="bkup-density-toggle"
        :class="{ active: showDensity }"
        title="页面密度"
        @click="showDensity = !showDensity"
      >
        <el-icon><Setting /></el-icon>
      </button>

      <el-button text :icon="Folder" @click="pathConfigVisible = true">路径配置</el-button>
    </template>

    <template #actions>
      <!-- 占位，右侧保留以备未来"新建"按钮 -->
    </template>

    <template #toolbar>
      <el-tabs v-model="activeTab" class="bkup-tabs" @tab-change="onTabChange">
        <el-tab-pane label="创建备份" name="create" />
        <el-tab-pane label="备份历史" name="history" />
      </el-tabs>
    </template>

    <router-view v-slot="{ Component }">
      <component :is="Component" />
    </router-view>

    <BackupPathConfig v-model="pathConfigVisible" />
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Folder, FolderOpened, Setting } from '@element-plus/icons-vue'
import PageWrapper from '@/components/PageWrapper.vue'
import BackupDensityPanel from '@/components/backup/BackupDensityPanel.vue'
import BackupPathConfig from '@/components/backup/BackupPathConfig.vue'
import { useBackupDensity } from '@/composables/useBackupDensity'

const { densityStyle } = useBackupDensity()
const showDensity = ref(false)
const pathConfigVisible = ref(false)

const route = useRoute()
const router = useRouter()

const nameToTabMap: Record<string, string> = {
  BackupCreate: 'create',
  BackupHistory: 'history',
}
const tabToNameMap: Record<string, string> = {
  create: 'BackupCreate',
  history: 'BackupHistory',
}

const activeTab = ref(
  nameToTabMap[route.name as string] || 'create',
)

function onTabChange(name: string | number) {
  const key = String(name)
  const target = tabToNameMap[key]
  if (target) router.push({ name: target })
}
</script>

<style scoped>
/* 与 StockInfoList 的全局页面元素同型；前缀 sil- → bkup- */
.bkup-page {
  --bkup-page-density: 1;
  --bkup-top-density: calc(var(--bkup-page-density));
  --bkup-middle-density: calc(var(--bkup-page-density));
  --bkup-bottom-density: calc(var(--bkup-page-density));

  --bkup-top-gap: calc(0.6rem * var(--bkup-top-density));
  --bkup-top-button-h: calc(2rem * var(--bkup-top-density));
  --bkup-top-input-h: calc(2rem * var(--bkup-top-density));

  --bkup-card-padding: calc(0.8rem * var(--bkup-page-density));
  --bkup-gap-lg: calc(0.6rem * var(--bkup-page-density));
  --bkup-gap-md: calc(0.4rem * var(--bkup-page-density));
  --bkup-gap-xl: calc(0.9rem * var(--bkup-page-density));

  --bkup-row-h: calc(2rem * var(--bkup-middle-density));
  --bkup-pagination-h: calc(2rem * var(--bkup-bottom-density));
}

.bkup-page :deep(.top-area__header) {
  min-height: var(--density-title-min, 32px);
  height: auto;
}
.bkup-page :deep(.top-area__title) {
  min-width: 0;
}

.bkup-title-icon {
  color: #2563eb;
  font-size: 1.1em;
}
.bkup-page-title {
  white-space: nowrap;
  font-weight: 700;
}

/* 密度开关按钮：放在 title 行末尾，跟路径配置按钮相邻 */
.bkup-density-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.625rem;
  height: 1.625rem;
  padding: 0;
  background: var(--color-card-bg, #ffffff);
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  cursor: pointer;
  color: #475569;
  transition: all 0.18s;
}
.bkup-density-toggle:hover {
  border-color: #93c5fd;
  color: #2563eb;
}
.bkup-density-toggle.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}
.bkup-density-toggle :deep(.el-icon) {
  font-size: 0.95rem;
}

/* Tabs 占满 top-area__toolbar */
.bkup-tabs {
  --el-tabs-header-height: calc(2rem * var(--bkup-top-density));
}
</style>