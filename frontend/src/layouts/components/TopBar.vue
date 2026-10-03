<template>
  <header class="topbar">
    <!-- Logo -->
    <div class="topbar-brand">
      <span class="brand-icon">📈</span>
      <span class="brand-text">智能金融归因分析平台</span>
    </div>

    <!-- 右侧信息 -->
    <div class="topbar-right">
      <template v-if="authStore.isLoggedIn">
        <el-dropdown trigger="click" @command="onCommand">
          <div class="user-info">
            <div class="user-avatar">{{ avatarText }}</div>
            <span class="user-name">
              {{ authStore.userInfo?.nickname || authStore.userInfo?.email || '未登录' }}
            </span>
            <el-tag
              v-if="authStore.isAdmin"
              type="danger"
              size="small"
              effect="dark"
              class="admin-badge"
            >
              ADMIN
            </el-tag>
            <el-icon class="user-arrow"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>
                {{ authStore.userInfo?.email }}
              </el-dropdown-item>
              <el-dropdown-item command="change-password" :icon="Lock">
                修改密码
              </el-dropdown-item>
              <el-dropdown-item command="logout" :icon="SwitchButton" divided>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
      <template v-else>
        <el-button type="primary" size="small" @click="router.push('/login')">
          登录
        </el-button>
      </template>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { ArrowDown, Lock, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

  const avatarText = computed(() => {
    const name =
      authStore.userInfo?.nickname ||
      authStore.userInfo?.email ||
      '?'
    return name.charAt(0).toUpperCase()
  })

async function onCommand(cmd: string) {
  if (cmd === 'logout') {
    try {
      await ElMessageBox.confirm('确认退出登录?', '提示', { type: 'warning' })
    } catch {
      return
    }
    await authStore.logout()
    ElMessageBox.close()
    router.push('/login')
  } else if (cmd === 'change-password') {
    router.push('/home/change-password')
  }
}
</script>

<style scoped>
.topbar {
  height: var(--topbar-height);
  background: var(--color-admin-surface);
  box-shadow: 0 1px 4px rgba(15, 21, 41, 0.08);
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

.admin-badge {
  font-weight: 700;
  letter-spacing: 0.4px;
}

.user-arrow {
  font-size: 12px;
  color: #9ca3af;
}
</style>