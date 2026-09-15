<template>
  <div class="not-found">
    <div class="content">
      <div class="emoji">🚧</div>
      <h1>404</h1>
      <p>页面不存在</p>
      <el-button type="primary" @click="router.push('/home/index')">
        返回首页
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<style scoped>
.not-found {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.content {
  text-align: center;
  color: #94a3b8;
}
.emoji { font-size: 4rem; margin-bottom: 12px; }
h1 { font-size: 3rem; color: #cbd5e1; font-weight: 800; }
p { margin: 12px 0 24px; }
</style>
