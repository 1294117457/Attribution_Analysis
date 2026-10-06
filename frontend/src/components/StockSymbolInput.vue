<!--
  StockSymbolInput — 6 位 A 股代码输入框

  统一处理：
    - 自动去除空格、自动补 0
    - 正则校验 (^\d{6}$)
    - 回车触发 onSubmit
    - 错误提示 (v-model 之外用 onChange 事件暴露清洗后的值)

  使用场景：DataBoard.vue、StockInfoList.vue、概念归属查询等。
-->
<template>
  <el-input
    :model-value="displayValue"
    :placeholder="placeholder"
    :style="{ width: `${width}px` }"
    :clearable="clearable"
    :maxlength="6"
    @update:model-value="onInput"
    @keyup.enter="onEnter"
    @blur="onBlur"
  >
    <template v-if="$slots.prefix" #prefix>
      <slot name="prefix" />
    </template>
  </el-input>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: string
  placeholder?: string
  width?: number
  clearable?: boolean
  /** 是否自动补 0（true: 输入少于 6 位自动左补 0；false: 仅清洗 trim） */
  autoPad?: boolean
}>(), {
  modelValue: '',
  placeholder: '股票代码 6 位 (如 000001 / 600519)',
  width: 220,
  clearable: true,
  autoPad: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'change', v: string, valid: boolean): void
  (e: 'submit', v: string): void
}>()

/** 清洗：去空白 → 自动补 0（如果开启） */
function clean(raw: string): string {
  const trimmed = (raw || '').trim()
  if (!trimmed) return ''
  return props.autoPad ? trimmed.padStart(6, '0') : trimmed
}

function isValid(s: string): boolean {
  return /^\d{6}$/.test(s)
}

const displayValue = computed(() => props.modelValue)

function onInput(v: string | number | undefined) {
  const raw = String(v ?? '')
  // 只允许输入数字（实时过滤非数字）
  const filtered = raw.replace(/[^\d]/g, '').slice(0, 6)
  emit('update:modelValue', filtered)
  emit('change', filtered, isValid(filtered))
}

function onEnter() {
  const v = clean(props.modelValue)
  if (v !== props.modelValue) emit('update:modelValue', v)
  emit('submit', v)
}

function onBlur() {
  if (props.autoPad) {
    const v = clean(props.modelValue)
    if (v !== props.modelValue) emit('update:modelValue', v)
  }
}

defineExpose({ clean, isValid })
</script>
