<!--
  RealtimePanel.vue — 实时查询占位面板

  ★ 契约（见 backend-java/docs/开发文档/采集模块/采集模块重构开发文档.md §7.5）：
    实时查询（strategy='realtime'）**本期只做占位**，不提供前端采集/试查入口。
    接口本身（GET /collect/query/{name}）保留，供业务侧后续直接调用。

  ⚠️ 为什么不让前端试查：
    实时查询是给**业务服务**调用的能力（如行情面板、概念 Tab 刷新），
    不是运维操作。放在采集管理页里会让人误以为「这里点一下就是采集」，
    而且实时数据不入库，采集历史里查不到任何记录 —— 审计断链。
-->
<template>
  <div class="realtime-panel">
    <CollectCard :title="item.label" :description="item.description">
      <template #tags>
        <el-tag size="small" type="danger" effect="plain">实时查询</el-tag>
      </template>

      <el-empty :image-size="72" description="实时查询接口建设中，暂不对外提供">
        <template #description>
          <div class="realtime-placeholder">
            <p>
              该接口为<b>实时直查</b>能力（不写入数据库），后续将开放给业务侧调用。
            </p>
            <p class="muted">
              接口地址：<code>GET /collect/query/{{ serviceName }}?params=&lt;JSON&gt;</code>
            </p>
            <p class="muted">
              采集方式：<code>strategy=realtime</code> ·
              实时直查：<code>{{ item.queryable ? '支持' : '不支持' }}</code>
            </p>
          </div>
        </template>
      </el-empty>
    </CollectCard>
  </div>
</template>

<script setup lang="ts">
import CollectCard from './CollectCard.vue'
import type { CatalogItem } from '../api'

defineProps<{
  serviceName: string
  item: CatalogItem
}>()
</script>

<style scoped>
.realtime-panel {
  flex: 1;
  min-height: 0;
}

.realtime-placeholder {
  font-size: 13px;
  color: #475569;
  line-height: 1.9;
}

.realtime-placeholder p {
  margin: 2px 0;
}

.realtime-placeholder code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 3px;
  color: #475569;
}

.muted {
  color: #94a3b8;
  font-size: 12px;
}
</style>
