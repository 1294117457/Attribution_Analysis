<!--
  CatalogTree.vue — 采集管理左侧目录树（step7 重构）

  - 数据源：useCatalog() 返回的 catalog（按 facet/sub_facet 二级聚合）
  - 选中：service_name（v-model）
  - 折叠状态持久化到 localStorage
-->
<template>
  <aside class="catalog-tree">
    <div v-if="loading" class="tip">加载中...</div>
    <div v-else-if="catalog.length === 0" class="tip">无采集任务</div>
    <div
      v-for="facet in catalog"
      :key="facet.facet"
      class="facet-block"
    >
      <div
        class="facet-header"
        role="button"
        :aria-expanded="!isCollapsed(facet.facet)"
        @click="toggleCollapsed(facet.facet)"
      >
        <el-icon class="collapse-arrow" :class="{ collapsed: isCollapsed(facet.facet) }"><ArrowDown /></el-icon>
        <el-icon class="mr-1">
          <TrendCharts v-if="facet.facet === 'tech'" />
          <Money v-else-if="facet.facet === 'capital'" />
          <PieChart v-else-if="facet.facet === 'fundamental'" />
          <Document v-else />
        </el-icon>
        <b>{{ facet.label }}</b>
        <span class="facet-badges">
          <el-badge v-if="countActive(facet) > 0" :value="countActive(facet)" type="success" />
        </span>
      </div>
      <div v-show="!isCollapsed(facet.facet)" class="sub-facet-list">
        <div
          v-for="(items, subKey) in facet.sub_groups"
          :key="subKey"
          class="sub-facet-block"
        >
          <div
            class="sub-facet-label"
            role="button"
            :aria-expanded="!isCollapsed(`${facet.facet}/${subKey}`)"
            @click="toggleCollapsed(`${facet.facet}/${subKey}`)"
          >
            <el-icon class="collapse-arrow" :class="{ collapsed: isCollapsed(`${facet.facet}/${subKey}`) }"><ArrowDown /></el-icon>
            {{ SUB_FACET_LABELS[subKey] || subKey }}
            <span class="sub-facet-count">{{ items.length }}</span>
          </div>
          <button
            v-show="!isCollapsed(`${facet.facet}/${subKey}`)"
            v-for="item in items"
            :key="item.service_name"
            class="task-btn"
            :class="{ active: active === item.service_name }"
            @click="active = item.service_name"
          >
            <el-tooltip :content="tooltipText(item)" placement="right" :show-after="300" popper-class="task-tip">
              <span class="task-btn-label">{{ item.label }}</span>
            </el-tooltip>
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ArrowDown, TrendCharts, Money, PieChart, Document } from '@element-plus/icons-vue'
import type { CatalogGroup, CatalogItem } from '../api'
import { countActive, SUB_FACET_LABELS } from '../composables/useCatalog'

defineProps<{
  catalog: CatalogGroup[]
  loading?: boolean
}>()

/** 当前选中的 service_name */
const active = defineModel<string>({ required: true })

// ── 折叠状态（key = facet 或 facet/subKey，持久化到 localStorage） ──
const COLLAPSE_STORAGE_KEY = 'collect-manage:collapsed'

function loadCollapsed(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(COLLAPSE_STORAGE_KEY) || '[]'))
  } catch {
    return new Set()
  }
}

const collapsed = ref<Set<string>>(loadCollapsed())

function isCollapsed(key: string): boolean {
  return collapsed.value.has(key)
}

function toggleCollapsed(key: string) {
  const next = new Set(collapsed.value)
  if (!next.delete(key)) next.add(key)
  collapsed.value = next
  localStorage.setItem(COLLAPSE_STORAGE_KEY, JSON.stringify([...next]))
}

/** 任务按钮的 hover 提示：描述 + 默认参数 + 实时/批量标识 */
function tooltipText(item: CatalogItem): string {
  const lines: string[] = []
  if (item.description) lines.push(item.description)
  if (item.kind === 'realtime') lines.push('实时查询接口（不写库）')
  else if (item.kind === 'both') lines.push('支持手动采集 + 实时查询')
  else lines.push('手动采集（写库）')
  const keys = Object.keys(item.default_params || {})
  if (keys.length) {
    const kv = keys
      .map((k) => `${k}=${JSON.stringify(item.default_params[k])}`)
      .join(', ')
    lines.push(`默认参数：${kv}`)
  }
  return lines.join('\n') || item.label
}
</script>

<style scoped>
.catalog-tree {
  width: 220px;
  flex-shrink: 0;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px 8px;
}

/*
  三层高度统一 26，字号递减 14 / 13 / 12，
  背景由深到浅、边框由深到浅，逐层缩进 8px
*/
.facet-block + .facet-block {
  margin-top: 10px;
}

/* ── 第一层：facet ── */
.facet-header {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 8px;
  font-size: 14px;
  color: #1e293b;
  background: #e2e8f0;
  border: 1px solid #94a3b8;
  border-left: 3px solid #3b82f6;
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
}

.facet-header:hover {
  background: #cbd5e1;
}

.facet-badges {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}

/* 无默认插槽的 el-badge 气泡是 <sup>：Tailwind preflight 给 sup 设了
   position: relative; top: -0.5em; line-height: 0，会把气泡整体上移 */
.facet-header :deep(.el-badge) {
  display: flex;
  align-items: center;
  line-height: 1;
}

.facet-header :deep(.el-badge__content) {
  position: static;
  top: auto;
  line-height: 1;
  vertical-align: middle;
}

.collapse-arrow {
  flex-shrink: 0;
  font-size: 12px;
  color: #94a3b8;
  transition: transform 0.15s;
}

.collapse-arrow.collapsed {
  transform: rotate(-90deg);
}

.sub-facet-list {
  margin-top: 4px;
  padding-left: 8px;
}

.sub-facet-block + .sub-facet-block {
  margin-top: 4px;
}

/* ── 第二层：sub_facet ── */
.sub-facet-label {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
}

.sub-facet-label:hover {
  background: #e2e8f0;
}

.sub-facet-count {
  margin-left: auto;
  font-size: 12px;
  font-weight: 400;
  color: #94a3b8;
}

/* ── 第三层：task ── */
.task-btn {
  display: block;
  width: calc(100% - 8px);
  height: 26px;
  margin: 2px 0 0 8px;
  padding: 0 8px;
  font-size: 12px;
  line-height: 24px;
  color: #475569;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.task-btn:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1e40af;
}

.task-btn.active {
  background: #dbeafe;
  border-color: #60a5fa;
  color: #1d4ed8;
  font-weight: 600;
}

.task-btn-label {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tip {
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

/* tooltip 让 \n 生效（scoped 下需 :global） */
:global(.task-tip) {
  max-width: 340px;
}
:global(.task-tip .el-popper__content) {
  line-height: 1.7;
  white-space: pre-line;
}
</style>
