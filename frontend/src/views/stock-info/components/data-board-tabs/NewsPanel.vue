<!--
 * components/data-board-tabs/NewsPanel.vue
 *
 * 新闻面 Tab — 抽屉 / 看板共用
 *
 * 现状：后端 /data-board/news 路由尚未实现，仅占位。
 * 抽到组件里是为以后两边能同步接 tushare news。
 -->
<template>
  <InfoCard title="📰 新闻资讯">
    <template #extra><el-tag type="warning" size="small">待实现</el-tag></template>
    <el-empty description="新闻面待 tushare news 权限开通后实现">
      <div class="text-xs text-gray-500">
        <p>当前占位任务：<code>news_article</code></p>
        <p>ORM 表：news_articles（未建）</p>
        <p>接口：tushare pro.news()</p>
        <p>状态：等待 tushare news 权限开通</p>
      </div>
    </el-empty>
  </InfoCard>
</template>

<script setup lang="ts">
// 抽屉 / 看板共用，无 props；占位组件
import InfoCard from '@/components/InfoCard.vue'
</script>
