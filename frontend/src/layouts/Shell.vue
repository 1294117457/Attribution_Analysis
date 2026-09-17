<template>
  <div class="shell">
    <TopBar class="shell-topbar" />
    <div class="shell-body">
      <LeftBar class="shell-sidebar" />
      <MainContainer class="shell-content" />
    </div>
  </div>
</template>

<script setup lang="ts">
import TopBar from './components/TopBar.vue'
import LeftBar from './components/LeftBar.vue'
import MainContainer from './components/MainContainer.vue'
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-rows: var(--topbar-height) 1fr;
  grid-template-columns: 1fr;
  height: 100vh;
  height: 100dvh;
  width: 100%;
  overflow: hidden;
}

.shell-topbar {
  grid-column: 1 / -1;
  grid-row: 1;
  z-index: 100;
}

.shell-body {
  display: flex;
  grid-row: 2;
  overflow: hidden;
  background: var(--color-admin-bg);
}

.shell-sidebar {
  flex-shrink: 0;
  z-index: 50;
}

.shell-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  contain: layout style;
}
</style>
