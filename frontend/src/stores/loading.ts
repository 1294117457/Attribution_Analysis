import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useLoadingStore = defineStore('loading', () => {
  const count = ref(0)
  const loading = ref(false)

  function start() {
    count.value++
    loading.value = true
  }

  function done() {
    count.value = Math.max(0, count.value - 1)
    if (count.value === 0) loading.value = false
  }

  return { count, loading, start, done }
})
