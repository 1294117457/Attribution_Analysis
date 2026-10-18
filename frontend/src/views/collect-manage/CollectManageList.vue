<!--
  CollectManageList.vue — 采集管理（step7 重构后简化版）

  简化前：3 个 tab（采集接口 / 调度计划 / 采集历史）
  简化后：1 个 tab（采集接口），调度计划和采集历史做占位卡片
  ── 后续如需补回 schedule / log 功能，参考旧版本恢复 el-tab-pane 即可

  配套：backend/src/contexts/collect/interface/router.py
-->
<template>
  <PageWrapper>
    <template #title>
      <el-icon class="mr-1"><Upload /></el-icon>
      采集管理
    </template>

    <el-tabs v-model="pageTab" class="page-tabs">
      <el-tab-pane label="采集接口" name="tasks" />
      <el-tab-pane label="调度计划" name="jobs" />
      <el-tab-pane label="采集历史" name="history" />
    </el-tabs>

    <!-- 调度计划：占位（APScheduler 暂未启用） -->
    <div v-show="pageTab === 'jobs'" class="placeholder-pane">
      <el-empty description="调度计划 / APScheduler 暂未启用（后续接入）">
        <template #image>
          <el-icon :size="48" color="#cbd5e1"><Clock /></el-icon>
        </template>
      </el-empty>
    </div>

    <!-- 采集历史：占位（运行日志后端未实现） -->
    <div v-show="pageTab === 'history'" class="placeholder-pane">
      <el-empty description="采集历史 / 运行日志 后端暂未实现（后续接入）">
        <template #image>
          <el-icon :size="48" color="#cbd5e1"><Document /></el-icon>
        </template>
      </el-empty>
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
import { Upload, Clock, Document } from '@element-plus/icons-vue'

import PageWrapper from '@/components/PageWrapper.vue'
import CatalogTree from './components/CatalogTree.vue'
import CollectTaskPane from './components/CollectTaskPane.vue'
import { useCatalog } from './composables/useCatalog'

const LOG_PREFIX = '[CollectManage]'

const { catalog, loading: catalogLoading, load: loadCatalog, getItem } = useCatalog()

// ── 页面标签：采集接口 / 调度计划（占位）/ 采集历史（占位） ─────
const pageTab = ref<'tasks' | 'jobs' | 'history'>('tasks')

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

/* 占位 tab 的容器（居中显示空状态） */
.placeholder-pane {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  border-radius: 8px;
}
</style>
