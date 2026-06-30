<template>
  <div class="app">
    <nav class="nav">
      <h1 class="title">智能金融数据归因分析平台</h1>
      <div class="nav-links">
        <router-link to="/">数据采集</router-link>
        <router-link to="/manage">数据管理</router-link>
      </div>
    </nav>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
  color: #333;
}

.app {
  min-height: 100vh;
}

.nav {
  background: #2c3e50;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 1.2rem;
  font-weight: 500;
}

.nav-links {
  display: flex;
  gap: 1.5rem;
}

.nav-links a {
  color: #fff;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background 0.2s;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  background: #34495e;
}

.main {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
