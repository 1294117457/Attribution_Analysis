<template>
  <div class="indicator-switcher flex items-center gap-3 flex-wrap">
    <!-- 主图指标 -->
    <div class="flex items-center gap-1">
      <span class="text-xs text-gray-500">主图:</span>
      <el-checkbox
        v-for="m in mainOptions"
        :key="m.value"
        :model-value="mainModel.includes(m.value)"
        size="small"
        @change="(v: boolean) => toggleMain(m.value, v)"
      >
        <span class="text-xs" :style="{ color: m.color }">{{ m.label }}</span>
      </el-checkbox>
    </div>

    <el-divider direction="vertical" class="!my-0" />

    <!-- 副图指标 -->
    <div class="flex items-center gap-1">
      <span class="text-xs text-gray-500">副图:</span>
      <el-radio-group v-model="subModel" size="small">
        <el-radio-button v-for="s in subOptions" :key="s.value" :value="s.value">
          <span class="text-xs">{{ s.label }}</span>
        </el-radio-button>
      </el-radio-group>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Option {
  label: string
  value: string
  color?: string
}

const props = defineProps<{
  main: string[]
  sub: string
}>()

const emit = defineEmits<{
  'update:main': [value: string[]]
  'update:sub': [value: string]
}>()

const mainModel = computed({
  get: () => props.main,
  set: (v) => emit('update:main', v),
})

const subModel = computed({
  get: () => props.sub,
  set: (v) => emit('update:sub', v),
})

const mainOptions: Option[] = [
  { label: 'MA5',  value: 'MA5',  color: '#fbbf24' },
  { label: 'MA10', value: 'MA10', color: '#3b82f6' },
  { label: 'MA20', value: 'MA20', color: '#a855f7' },
  { label: 'MA60', value: 'MA60', color: '#06b6d4' },
  { label: 'BOLL', value: 'BOLL', color: '#a855f7' },
]

const subOptions: Option[] = [
  { label: '无',   value: '' },
  { label: 'MACD', value: 'MACD' },
  { label: 'RSI',  value: 'RSI' },
  { label: 'KDJ',  value: 'KDJ' },
]

function toggleMain(value: string, checked: boolean) {
  const cur = [...mainModel.value]
  const idx = cur.indexOf(value)
  if (checked && idx < 0) {
    cur.push(value)
  } else if (!checked && idx >= 0) {
    cur.splice(idx, 1)
  }
  emit('update:main', cur)
}
</script>

<style scoped>
.indicator-switcher {
  padding: 6px 0;
  border-bottom: 1px solid #f0f2f5;
}
</style>