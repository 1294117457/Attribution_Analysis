<!--
 * components/DetailDrawer.vue
 *
 * 详情抽屉统一骨架（规范见 docs/frontend-docs/detail-drawer-guide.md）
 *
 *   top-button-area  固定高度，一行横排方形按钮 + 右侧关闭；底部实线 + 阴影
 *   baseinfo-area    区块标题 + 字段网格，高度随内容
 *   main-area        区块标题 + 面板：1 个直接显示，多个自动改为 Tab
 *
 * baseinfo + main 作为一个整体滚动，二者之间用灰色色带分隔。
 * 任何区域的内部组件都不能撑宽抽屉：宽度一律以抽屉为准，超出部分由组件自己处理。
 -->
<template>
  <el-drawer
    v-model="visible"
    :size="size"
    direction="rtl"
    :with-header="false"
    class="detail-drawer"
  >
    <div class="top-button-area">
      <div class="top-button-area__actions">
        <button
          v-for="a in actions"
          :key="a.key"
          type="button"
          class="square-action"
          :class="`square-action--${a.type ?? 'default'}`"
          :disabled="a.disabled"
          :title="a.label"
          @click="emit('action', a.key)"
        >
          <el-icon :size="16"><component :is="a.icon" /></el-icon>
          <span class="square-action__label">{{ a.label }}</span>
        </button>
      </div>
      <button type="button" class="top-button-area__close" aria-label="关闭" title="关闭" @click="visible = false">
        <el-icon :size="16"><Close /></el-icon>
      </button>
    </div>

    <div class="detail-drawer__scroll">
      <section class="drawer-section baseinfo-area">
        <div class="drawer-section__head">
          <h3 class="drawer-section__title">{{ baseinfoTitle }}</h3>
        </div>
        <dl v-if="fields?.length" class="baseinfo-area__fields">
          <div v-for="f in fields" :key="f.label" class="baseinfo-area__field">
            <dt>{{ f.label }}：</dt>
            <dd>{{ f.value ?? '—' }}</dd>
          </div>
        </dl>
        <slot name="baseinfo" />
      </section>

      <section class="drawer-section main-area">
        <div class="drawer-section__head">
          <h3 class="drawer-section__title">{{ mainTitle }}</h3>
          <el-tabs v-if="panels.length > 1" v-model="active" stretch class="main-area__tabs">
            <el-tab-pane v-for="p in panels" :key="p.name" :label="p.label" :name="p.name" />
          </el-tabs>
        </div>
        <div
          v-for="p in panels"
          v-show="panels.length === 1 || active === p.name"
          :key="p.name"
          class="main-area__panel"
        >
          <slot :name="`panel-${p.name}`" />
        </div>
      </section>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { watch, type Component } from 'vue'
import { Close } from '@element-plus/icons-vue'

export interface DetailDrawerAction {
  key: string
  label: string
  icon: Component
  type?: 'default' | 'primary' | 'success' | 'warning' | 'danger'
  disabled?: boolean
}

export interface DetailDrawerField {
  label: string
  value?: string | number | null
}

export interface DetailDrawerPanel {
  name: string
  label: string
}

const props = withDefaults(defineProps<{
  size?: string | number
  actions?: DetailDrawerAction[]
  baseinfoTitle?: string
  fields?: DetailDrawerField[]
  mainTitle?: string
  panels?: DetailDrawerPanel[]
}>(), {
  size: '480px',
  actions: () => [],
  baseinfoTitle: '基本信息',
  mainTitle: '详细数据',
  panels: () => [],
})

const emit = defineEmits<{ action: [key: string] }>()

const visible = defineModel<boolean>({ required: true })
const active = defineModel<string>('active', { default: '' })

watch(visible, (v) => {
  if (v && props.panels.length) active.value = props.panels[0].name
}, { immediate: true })
</script>

<!-- el-drawer 的 class 落在 .el-drawer 上，但不带本组件 scoped 属性，:deep 不可靠，这里用非 scoped 限定 -->
<style>
.detail-drawer .el-drawer__body {
  display: flex;
  flex-direction: column;
  padding: 0;
  min-width: 0;
  overflow: hidden;
  background: #f1f5f9;
}
</style>

<style scoped>
/* ── top-button-area：贴顶通栏，按钮无间距、以分隔线区分；底部实线 + 阴影 ── */
.top-button-area {
  position: relative;
  z-index: 3;
  flex: 0 0 48px;
  height: 48px;
  display: flex;
  align-items: stretch;
  min-width: 0;
  background: #fff;
  border-bottom: 1px solid #cbd5e1;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}
.top-button-area__actions {
  flex: 1;
  min-width: 0;
  display: flex;
  overflow-x: auto;
}

.square-action,
.top-button-area__close {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  border-radius: 0;
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s, box-shadow 0.15s;
}

.square-action {
  --btn-color: #475569;
  --btn-bg: #fff;
  --btn-bg-hover: #f1f5f9;
  flex: 0 0 60px;
  width: 60px;
  gap: 2px;
  border-right: 1px solid #cbd5e1;
  background: var(--btn-bg);
  color: var(--btn-color);
}
.square-action:hover:not(:disabled) { background: var(--btn-bg-hover); }
.square-action:active:not(:disabled) { box-shadow: inset 0 2px 4px rgba(15, 23, 42, 0.15); }
.square-action:disabled { opacity: 0.5; cursor: not-allowed; }
.square-action__label {
  font-size: 11px;
  line-height: 1.2;
  white-space: nowrap;
}
.square-action--primary { --btn-color: var(--el-color-primary); --btn-bg: var(--el-color-primary-light-9); --btn-bg-hover: var(--el-color-primary-light-8); }
.square-action--success { --btn-color: var(--el-color-success); --btn-bg: var(--el-color-success-light-9); --btn-bg-hover: var(--el-color-success-light-8); }
.square-action--warning { --btn-color: var(--el-color-warning); --btn-bg: var(--el-color-warning-light-9); --btn-bg-hover: var(--el-color-warning-light-8); }
.square-action--danger  { --btn-color: var(--el-color-danger);  --btn-bg: var(--el-color-danger-light-9);  --btn-bg-hover: var(--el-color-danger-light-8); }

.top-button-area__close {
  flex: 0 0 48px;
  margin-left: auto;
  border-left: 1px solid #cbd5e1;
  background: #fff;
  color: #64748b;
}
.top-button-area__close:hover {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

/* ── 滚动区：预留滚动条位置，宽度不随内容高度变化；禁止横向撑开 ── */
.detail-drawer__scroll {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

/* ── 区块：白底卡片，之间用 8px 灰色色带分隔 ────────────── */
.drawer-section {
  min-width: 0;
  overflow-x: clip;
  padding: 4px 16px 12px;
  background: #fff;
}
.drawer-section + .drawer-section { margin-top: 8px; }
.drawer-section > :deep(*),
.main-area__panel > :deep(*) {
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
.drawer-section__head {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
  margin-bottom: 8px;
}
.drawer-section__title {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  line-height: 40px;
  color: #0f172a;
}
.drawer-section__title::before {
  content: '';
  width: 3px;
  height: 16px;
  border-radius: 2px;
  background: var(--el-color-primary);
}

/* ── baseinfo-area：高度随内容 ─────────────────────────── */
.baseinfo-area__fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 16px;
  margin: 0;
}
.baseinfo-area__field {
  display: flex;
  min-width: 0;
  font-size: 12px;
  line-height: 1.6;
}
.baseinfo-area__field dt {
  flex: 0 0 auto;
  color: #94a3b8;
}
.baseinfo-area__field dd {
  margin: 0;
  min-width: 0;
  color: #1e293b;
  word-break: break-all;
}

/* ── main-area：标题右侧放 Tab 头，内容在下方；高度随内容 ── */
.main-area__tabs {
  flex: 1;
  min-width: 0;
}
.main-area__tabs :deep(.el-tabs__header) { margin: 0; }
.main-area__tabs :deep(.el-tabs__item) {
  padding: 0 6px;
  font-size: 13px;
}
.main-area__tabs :deep(.el-tabs__content) { display: none; }
.main-area__panel { min-width: 0; }
/* 面板内卡片统一为 InfoCard；面板与数据看板共用，抽屉内只收紧卡片间距 */
.main-area__panel > :deep(*) { gap: var(--info-card-gap); }
</style>
