<template>
  <div class="account-page page-wrapper">
    <header class="page-header">
      <div>
        <h1 class="page-title">账户管理</h1>
        <p class="page-subtitle">查看用户、分配角色、对照权限矩阵</p>
      </div>
      <div class="header-actions">
        <el-tag type="success" effect="light">
          管理员视角
        </el-tag>
      </div>
    </header>

    <el-tabs v-model="activeTab" class="account-tabs">
      <!-- ── 账户数据 ───────────────────────────────────── -->
      <el-tab-pane label="账户" name="users">
        <div class="toolbar">
          <el-input
            v-model="keyword"
            placeholder="搜索邮箱 / 昵称"
            clearable
            style="width: 280px"
            :prefix-icon="Search"
            @input="debouncedReload"
          />
          <el-select
            v-model="activeFilter"
            placeholder="状态"
            clearable
            style="width: 140px"
            @change="reload"
          >
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
          <el-button :icon="Refresh" @click="reload">刷新</el-button>
        </div>

        <el-table
          v-loading="userLoading"
          :data="userList"
          stripe
          border
          style="width: 100%"
          empty-text="暂无用户"
        >
          <el-table-column type="index" label="#" width="56" />
          <el-table-column prop="id" label="ID" width="64" />
          <el-table-column label="账号 / 邮箱" min-width="220">
            <template #default="{ row }">
              <span class="email-cell">{{ row.email }}</span>
            </template>
          </el-table-column>
          <el-table-column label="昵称" min-width="140">
            <template #default="{ row }">{{ row.nickname || '—' }}</template>
          </el-table-column>
          <el-table-column label="角色" min-width="220">
            <template #default="{ row }">
              <el-tag
                v-for="role in row.roles"
                :key="role.id"
                :type="role.code === 'admin' ? 'danger' : role.code === 'member' ? 'primary' : 'info'"
                size="small"
                effect="light"
                class="role-tag"
              >
                {{ role.name }}
              </el-tag>
              <span v-if="!row.roles.length" class="muted">未分配</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                {{ row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="最后登录" min-width="160">
            <template #default="{ row }">
              <span class="muted">{{ row.last_login_at || '从未' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="280" fixed="right">
            <template #default="{ row }">
              <el-button
                size="small"
                :type="row.is_active ? 'warning' : 'success'"
                :disabled="!canManage"
                @click="handleToggleStatus(row)"
              >
                {{ row.is_active ? '禁用' : '启用' }}
              </el-button>
              <el-button
                size="small"
                :disabled="!canManage"
                @click="openResetPasswordDialog(row)"
              >
                重置密码
              </el-button>
              <el-button
                size="small"
                type="primary"
                :disabled="!canManage"
                @click="openAssignRoleDialog(row)"
              >
                分配角色
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          class="pager"
          @current-change="reload"
          @size-change="reload"
        />
      </el-tab-pane>

      <!-- ── 角色 ──────────────────────────────────────── -->
      <el-tab-pane label="角色" name="roles">
        <el-table v-loading="roleLoading" :data="roleList" stripe border style="width: 100%">
          <el-table-column prop="code" label="编码" min-width="140" />
          <el-table-column prop="name" label="名称" min-width="160" />
          <el-table-column label="系统内置" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.is_system" type="warning" size="small">内置</el-tag>
              <el-tag v-else type="info" size="small">自定义</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sort_order" label="排序" width="100" />
          <el-table-column label="说明" min-width="200">
            <template #default="{ row }">
              <span class="muted">{{ row.description || '—' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ── 权限 ──────────────────────────────────────── -->
      <el-tab-pane label="权限" name="permissions">
        <el-collapse v-model="expandedResources" class="perm-collapse">
          <el-collapse-item
            v-for="(items, resource) in groupedPermissions"
            :key="resource"
            :name="resource"
            :title="`${resource}（${items.length} 项）`"
          >
            <div class="perm-grid">
              <el-tag
                v-for="p in items"
                :key="p.id"
                class="perm-tag"
                :type="actionTagType(p.action)"
                effect="light"
              >
                {{ p.code }}
              </el-tag>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-tab-pane>
    </el-tabs>

    <!-- ── 重置密码对话框 ──────────────────────────────── -->
    <el-dialog v-model="resetDialog.visible" title="重置密码" width="420px">
      <el-form ref="resetFormRef" :model="resetDialog.form" :rules="resetRules" label-width="80px">
        <el-form-item label="目标用户">
          <span class="muted">{{ resetDialog.user?.email }}</span>
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="resetDialog.form.new_password"
            type="password"
            show-password
            placeholder="8-64 位"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="resetDialog.loading" @click="confirmResetPassword">
          确认重置
        </el-button>
      </template>
    </el-dialog>

    <!-- ── 分配角色对话框 ──────────────────────────────── -->
    <el-dialog v-model="roleDialog.visible" title="分配角色" width="420px">
      <el-form label-width="80px">
        <el-form-item label="目标用户">
          <span class="muted">{{ roleDialog.user?.email }}</span>
        </el-form-item>
        <el-form-item label="已有角色">
          <el-tag
            v-for="r in roleDialog.user?.roles || []"
            :key="r.id"
            class="role-tag"
            closable
            @close="removeRole(roleDialog.user!, r.id)"
          >
            {{ r.name }}
          </el-tag>
          <span v-if="!roleDialog.user?.roles?.length" class="muted">无</span>
        </el-form-item>
        <el-form-item label="添加角色">
          <el-select v-model="roleDialog.toAssign" placeholder="选择角色" style="width: 100%">
            <el-option
              v-for="r in assignableRoles"
              :key="r.id"
              :label="`${r.name}（${r.code}）`"
              :value="r.id"
              :disabled="roleDialog.user?.roles?.some((x) => x.id === r.id)"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialog.visible = false">关闭</el-button>
        <el-button
          type="primary"
          :disabled="!roleDialog.toAssign"
          :loading="roleDialog.loading"
          @click="confirmAssignRole"
        >
          分配
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import {
  listUsers,
  updateUserStatus,
  resetUserPassword,
  assignRole,
  removeRole,
  listRoles,
  listPermissions,
  type UserInfo,
  type Role,
  type Permission,
} from './api'

// 暂去掉 RBAC 限制：登录用户均可管理（rbac 后续接入）
const canManage = computed(() => true)

const activeTab = ref<'users' | 'roles' | 'permissions'>('users')

// ── 账户数据 ────────────────────────────────────────────────
const userLoading = ref(false)
const userList = ref<UserInfo[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const activeFilter = ref<boolean | undefined>(undefined)

async function reload() {
  userLoading.value = true
  try {
    const res = await listUsers({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      is_active: activeFilter.value,
    })
    userList.value = res.items
    total.value = res.total
  } finally {
    userLoading.value = false
  }
}

let reloadTimer: ReturnType<typeof setTimeout> | null = null
function debouncedReload() {
  if (reloadTimer) clearTimeout(reloadTimer)
  reloadTimer = setTimeout(() => {
    page.value = 1
    reload()
  }, 300)
}

async function handleToggleStatus(row: UserInfo) {
  const target = !row.is_active
  try {
    await ElMessageBox.confirm(
      `确认要${target ? '启用' : '禁用'}用户「${row.email}」吗？${target ? '' : '该用户将被强制下线。'}`,
      '提示',
      { type: 'warning' },
    )
  } catch {
    return
  }
  await updateUserStatus(row.id, { is_active: target })
  ElMessage.success(target ? '已启用' : '已禁用')
  await reload()
}

// ── 重置密码 ────────────────────────────────────────────────
interface ResetDialogState {
  visible: boolean
  loading: boolean
  user: UserInfo | null
  form: { new_password: string }
}
const resetDialog = reactive<ResetDialogState>({
  visible: false,
  loading: false,
  user: null,
  form: { new_password: '' },
})
const resetFormRef = ref<FormInstance>()
const resetRules: FormRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度 8-64 位', trigger: 'blur' },
  ],
}
function openResetPasswordDialog(row: UserInfo) {
  resetDialog.user = row
  resetDialog.form.new_password = ''
  resetDialog.visible = true
}
async function confirmResetPassword() {
  if (!resetDialog.user || !resetFormRef.value) return
  try {
    await resetFormRef.value.validate()
  } catch {
    return
  }
  resetDialog.loading = true
  try {
    await resetUserPassword(resetDialog.user.id, {
      new_password: resetDialog.form.new_password,
    })
    ElMessage.success('密码已重置，该用户全部设备已下线')
    resetDialog.visible = false
  } finally {
    resetDialog.loading = false
  }
}

// ── 分配角色 ────────────────────────────────────────────────
interface RoleDialogState {
  visible: boolean
  loading: boolean
  user: UserInfo | null
  toAssign: number | null
}
const roleDialog = reactive<RoleDialogState>({
  visible: false,
  loading: false,
  user: null,
  toAssign: null,
})

async function openAssignRoleDialog(row: UserInfo) {
  roleDialog.user = row
  roleDialog.toAssign = null
  await loadRoles()
  roleDialog.visible = true
}

async function confirmAssignRole() {
  if (!roleDialog.user || !roleDialog.toAssign) return
  roleDialog.loading = true
  try {
    await assignRole(roleDialog.user.id, { role_id: roleDialog.toAssign })
    ElMessage.success('已分配')
    roleDialog.toAssign = null
    // 刷新当前用户的角色
    if (roleDialog.user) {
      const refreshed = await listUsers({ page: 1, page_size: 200 })
      const u = refreshed.items.find((x) => x.id === roleDialog.user!.id)
      if (u) roleDialog.user = u
    }
    await reload()
  } finally {
    roleDialog.loading = false
  }
}

async function removeRole(user: UserInfo, roleId: number) {
  try {
    await ElMessageBox.confirm('确认解除该角色吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  await removeRole2(user.id, roleId)
}

async function removeRole2(userId: number, roleId: number) {
  await removeRole(userId, roleId)
  ElMessage.success('已解除')
  if (roleDialog.user) {
    const refreshed = await listUsers({ page: 1, page_size: 200 })
    const u = refreshed.items.find((x) => x.id === roleDialog.user!.id)
    if (u) roleDialog.user = u
  }
  await reload()
}

// ── 角色 / 权限 ─────────────────────────────────────────────
const roleLoading = ref(false)
const roleList = ref<Role[]>([])

async function loadRoles() {
  if (roleList.value.length) return
  roleLoading.value = true
  try {
    roleList.value = await listRoles()
  } finally {
    roleLoading.value = false
  }
}

const permissionList = ref<Permission[]>([])
const groupedPermissions = computed(() => {
  const grouped: Record<string, Permission[]> = {}
  for (const p of permissionList.value) {
    ;(grouped[p.resource] ??= []).push(p)
  }
  return grouped
})

const assignableRoles = computed(() =>
  roleList.value.filter((r) => !r.is_system || r.code !== 'admin'),
)

const expandedResources = ref<string[]>([])

function actionTagType(action: string): 'success' | 'warning' | 'danger' | 'info' {
  if (action === 'read') return 'success'
  if (action === 'write') return 'warning'
  if (action === 'delete') return 'danger'
  return 'info'
}

onMounted(async () => {
  await reload()
  await loadRoles()
  permissionList.value = await listPermissions()
  // 默认展开所有
  expandedResources.value = Object.keys(groupedPermissions.value)
})

watch(activeTab, (v) => {
  if (v === 'roles' && !roleList.value.length) loadRoles()
})
</script>

<style scoped>
.account-page {
  padding: var(--density-card-padding);
  background: var(--color-admin-bg);
  display: flex;
  flex-direction: column;
  gap: var(--density-gap-xl);
  min-height: 100%;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: var(--density-title-min);
}

.page-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-admin-text);
}

.page-subtitle {
  font-size: 0.85rem;
  color: var(--color-admin-muted);
  margin-top: 4px;
}

.account-tabs :deep(.el-tabs__item) {
  font-size: 0.95rem;
  font-weight: 600;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
  display: flex;
}

.role-tag {
  margin-right: 6px;
  margin-bottom: 2px;
}

.muted {
  color: var(--color-admin-muted);
  font-size: 0.85rem;
}

.email-cell {
  font-family: 'Courier New', monospace;
  color: #1e293b;
}

.perm-collapse {
  background: var(--color-admin-surface);
  border-radius: 12px;
  padding: 8px 16px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.perm-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.perm-tag {
  font-family: 'Courier New', monospace;
}
</style>