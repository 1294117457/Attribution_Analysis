<!--
  CollectManageList.vue — 采集管理

  结构：
    - 采集接口：左 CatalogTree（目录树）+ 右 CollectTaskPane（工具栏 + 任务列表），左右各自独立滚动
    - 采集方案：PlanList

  配套：docs/dev/step2/02datamanage/01-采集管理四维重构方案.md §3.2
-->
<template>
  <PageWrapper>
    <template #title>
      <el-icon class="mr-1"><Upload /></el-icon>
      采集管理
    </template>

    <el-tabs v-model="pageTab" class="page-tabs">
      <el-tab-pane label="采集接口" name="tasks" />
      <el-tab-pane label="采集方案" name="plans" />
    </el-tabs>

    <PlanList v-if="pageTab === 'plans'" />

    <div v-show="pageTab === 'tasks'" class="layout-body">
      <CatalogTree v-model="activeTaskType" :catalog="catalog" :loading="catalogLoading" />
      <CollectTaskPane :task-type="activeTaskType" :task-def="currentTaskDef" />
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Upload } from '@element-plus/icons-vue'

import PageWrapper from '@/components/PageWrapper.vue'
import CatalogTree from './components/CatalogTree.vue'
import CollectTaskPane from './components/CollectTaskPane.vue'
import PlanList from './components/PlanList.vue'
import { useCatalog } from './composables/useCatalog'

const LOG_PREFIX = '[CollectManage]'

const { catalog, loading: catalogLoading, load: loadCatalog, getTaskDef } = useCatalog()

// ── 页面标签：采集接口 / 采集方案 ──────────────────────────
const pageTab = ref<'tasks' | 'plans'>('tasks')

// ── 当前选中 task_type ────────────────────────────────────────
const activeTaskType = ref<string>('daily_kline')
const currentTaskDef = computed(() => getTaskDef(activeTaskType.value))

onMounted(async () => {
  console.log(LOG_PREFIX, 'mounted, loading catalog')
  await loadCatalog()
})
</script>

<style scoped>
.page-tabs {
  flex-shrink: 0;
  margin-bottom: 4px;
}

/* 占满 PageWrapper 剩余高度，左右两栏各自内部滚动 */
.layout-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 16px;
  align-items: stretch;
  overflow: hidden;
}
</style>
