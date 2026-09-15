<template>
  <aside class="leftbar" :class="{ collapsed }">
    <!-- 折叠按钮 -->
    <div class="collapse-btn" @click="collapsed = !collapsed">
      <el-icon size="16">
        <Fold v-if="!collapsed" />
        <Expand v-else />
      </el-icon>
    </div>

    <!-- 菜单 -->
    <el-menu
      :default-active="activePath"
      :collapse="collapsed"
      :collapse-transition="false"
      class="leftbar-menu"
      background-color="transparent"
      text-color="#a8b3cf"
      active-text-color="#2563eb"
    >
      <template v-for="item in menuItems" :key="item.path">
        <el-menu-item
          v-if="!item.children?.length"
          :index="item.path"
          @click="navigate(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>
            <span>{{ item.title }}</span>
          </template>
        </el-menu-item>

        <el-sub-menu v-else :index="item.path">
          <template #title>
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </template>
          <el-menu-item
            v-for="sub in item.children"
            :key="sub.path"
            :index="sub.path"
            @click="navigate(sub.path)"
          >
            <span>{{ sub.title }}</span>
          </el-menu-item>
        </el-sub-menu>
      </template>
    </el-menu>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Fold,
  Expand,
  DataLine,
  Folder,
  Odometer,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const collapsed = ref(false)

const activePath = computed(() => route.path)

interface MenuItem {
  path: string
  title: string
  icon: string
  children?: MenuItem[]
}

const menuItems: MenuItem[] = [
  { path: '/home/index',      title: '数据大盘', icon: Odometer },
  { path: '/home/stock-panel', title: '股票信息', icon: DataLine },
  { path: '/home/pool',       title: '操作池',   icon: Folder },
]

function navigate(path: string) {
  router.push(path)
}
</script>

<style scoped>
.leftbar {
  width: var(--sidebar-width);
  background: var(--color-sidebar-bg);
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  overflow: hidden;
  position: relative;
}

.leftbar.collapsed {
  width: var(--sidebar-collapsed);
}

/* 折叠按钮 */
.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 10px;
  height: 36px;
  cursor: pointer;
  color: #5c6b8a;
  transition: color 0.2s;
  flex-shrink: 0;
}
.collapse-btn:hover { color: #93a5c6; }

/* 菜单 */
.leftbar-menu {
  border-right: none !important;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Element Plus menu 覆盖 */
:deep(.el-menu) {
  border-right: none !important;
  background-color: transparent !important;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: var(--color-sidebar-text) !important;
  height: 44px !important;
  line-height: 44px !important;
  margin: 2px 8px !important;
  border-radius: 8px !important;
  transition: background 0.2s, color 0.2s !important;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, 0.06) !important;
  color: #fff !important;
}

:deep(.el-menu-item.is-active) {
  background: var(--color-sidebar-active-bg) !important;
  color: var(--color-sidebar-active-text) !important;
}

:deep(.el-sub-menu .el-menu-item) {
  padding-left: 20px !important;
  font-size: 12px !important;
  min-width: 0 !important;
}

:deep(.el-sub-menu .el-menu-item.is-active) {
  background: var(--color-sidebar-active-bg) !important;
  color: var(--color-sidebar-active-text) !important;
}

:deep(.el-icon) {
  color: inherit !important;
}

:deep(.el-sub-menu__title) {
  padding-left: 12px !important;
}

:deep(.el-menu-item) {
  padding-left: 12px !important;
}

/* collapsed 时文字不显示 */
.collapsed :deep(.el-menu-item span),
.collapsed :deep(.el-sub-menu__title span),
.collapsed :deep(.el-sub-menu .el-menu-item span) {
  display: none;
}
</style>
