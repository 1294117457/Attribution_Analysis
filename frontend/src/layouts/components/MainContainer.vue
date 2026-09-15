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
  overflow-y: auto;
  background: var(--color-admin-bg);
  padding-top: 16px;
}

.page-container {
  width: min(100%, 1440px);
  margin: 0 auto;
  padding-right: 16px;
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
