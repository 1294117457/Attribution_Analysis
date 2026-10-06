<!--
  数据看板 · 新闻面 Tab (news)
  当前数据源待 tushare news 权限开通，本期只展示占位卡片。
-->
<template>
  <div class="news-panel">
    <el-card shadow="never">
      <template #header>
        <span class="font-bold">📰 新闻资讯</span>
        <el-tag type="warning" size="small" class="ml-2">待实现</el-tag>
      </template>
      <el-empty :description="news?.message || '新闻面待 tushare news 权限开通后实现'">
        <div class="text-xs text-gray-500 news-meta">
          <p>当前占位任务：<code>news_article</code></p>
          <p>ORM 表：news_articles（未建）</p>
          <p>接口：tushare pro.news()</p>
          <p>状态：等待 tushare news 权限开通</p>
        </div>
      </el-empty>
    </el-card>

    <!-- 预留：未来可能的板块 -->
    <el-card shadow="never" class="mt-2">
      <template #header>
        <span class="font-bold">📅 未来可扩展</span>
      </template>
      <ul class="text-sm text-gray-600 news-future">
        <li>📊 个股公告（tushare pro.anns）</li>
        <li>📰 财经快讯（tushare pro.news）</li>
        <li>🔍 研报数据（tushare pro.report_rc）</li>
        <li>💬 互动易问答（同花顺问财 / 富途牛牛 API）</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
// news 来自父组件 overview（异步加载），初始可能为 undefined
// 这里给默认兜底，保证 NewsPanel 单独渲染时也不会炸
const props = withDefaults(defineProps<{
  news?: { available: boolean; message: string } | null
}>(), {
  news: () => ({ available: false, message: '新闻面待 tushare news 权限开通后实现' }),
})

const news = computed(() => props.news)
</script>

<style scoped>
.news-panel { padding: 0.5rem 0; }
.news-meta { text-align: left; max-width: 400px; margin: 0 auto; }
.news-meta code {
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: ui-monospace, monospace;
}
.news-future {
  list-style: none;
  padding: 0;
  margin: 0;
}
.news-future li {
  padding: 0.4rem 0;
  border-bottom: 1px dashed #f1f5f9;
}
.news-future li:last-child { border-bottom: none; }
.mt-2 { margin-top: 0.5rem; }
.font-bold { font-weight: 700; }
.ml-2 { margin-left: 0.5rem; }
</style>