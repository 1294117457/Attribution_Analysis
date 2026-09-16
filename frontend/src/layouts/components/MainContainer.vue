<template>
  <div class="main-container">
    <div class="page-container">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.main-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--color-admin-bg);
  display: flex;
  flex-direction: column;
}

.page-container {
  flex: 1;
  min-height: 0;
  width: min(100%, 1440px);
  margin: 0 auto;
  padding: 16px 16px 16px;
  display: flex;
  flex-direction: column;
}

/* 路由切换过渡 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
