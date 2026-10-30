<!--
  CollectManageList.vue — 采集管理（全异步任务式）

  两个 tab：
  - 采集接口：左树 + 右任务面板（建任务→轮询进度）
  - 采集历史：CollectHistoryPane（Java 查 PG collect_logs）

  注：原「调度计划」tab（Quartz 占位）已移除 —— collect_schedule / collect_run_log
  两表已删除、attribution-scheduler 模块已下线，当前无定时采集能力。
-->
<template>
    <PageWrapper>
    <template #title>
      <el-icon class="mr-1"><Upload /></el-icon>
      采集管理
    </template>

    <el-tabs v-model="pageTab" class="page-tabs">
      <el-tab-pane label="采集接口" name="tasks" />
      <el-tab-pane label="采集历史" name="history" />
    </el-tabs>

    <!-- 采集历史：PG collect_logs 永久审计 -->
    <div v-show="pageTab === 'history'" class="layout-body">
      <CollectHistoryPane />
    </div>

    <!-- 采集接口：左树 + 右任务面板（核心功能） -->
    <div v-show="pageTab === 'tasks'" class="layout-body">
      <CatalogTree
        v-model="activeServiceName"
        :catalog="catalog"
        :loading="catalogLoading"
      />
      <CollectTaskPane
        :service-name="activeServiceName"
        :item="currentItem"
      />
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Upload } from '@element-plus/icons-vue'

import PageWrapper from '@/components/PageWrapper.vue'
import CatalogTree from './components/CatalogTree.vue'
import CollectTaskPane from './components/CollectTaskPane.vue'
import CollectHistoryPane from './components/CollectHistoryPane.vue'
import { useCatalog } from './composables/useCatalog'

const LOG_PREFIX = '[CollectManage]'

const { catalog, loading: catalogLoading, load: loadCatalog, getItem } = useCatalog()

// ── 页面标签：采集接口 / 采集历史 ───────────
const pageTab = ref<'tasks' | 'history'>('tasks')

// ── 当前选中 service_name ──────────────────────────────────
const activeServiceName = ref<string>('daily_kline')
const currentItem = computed(() => getItem(activeServiceName.value))

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
