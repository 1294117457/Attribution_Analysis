<template>
  <header class="topbar">
    <!-- Logo -->
    <div class="topbar-brand">
      <span class="brand-icon">📈</span>
      <span class="brand-text">智能金融归因分析平台</span>
    </div>

    <!-- 右侧信息 -->
    <div class="topbar-right">
      <el-dropdown trigger="click">
        <div class="user-info">
          <div class="user-avatar">管</div>
          <span class="user-name">管理员</span>
          <el-icon class="user-arrow"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item>个人设置</el-dropdown-item>
            <el-dropdown-item divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ArrowDown } from '@element-plus/icons-vue'
</script>

<style scoped>
.topbar {
  height: var(--topbar-height);
  background: var(--color-admin-surface);
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  position: relative;
  z-index: 10;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-icon {
  font-size: 1.2rem;
}

.brand-text {
  font-size: 0.95rem;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: 0.3px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-info:hover {
  background: #f1f5f9;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.user-name {
  font-size: 13px;
  color: #374151;
  font-weight: 500;
}

.user-arrow {
  font-size: 12px;
  color: #9ca3af;
}
</style>
