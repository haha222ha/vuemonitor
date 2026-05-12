import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/utils/api'

export const useBenchmarkStore = defineStore('benchmark', () => {
  const benchmarks = ref([])
  const distribution = ref([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchBenchmarks(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/admin/benchmark', { params })
      benchmarks.value = data.items || []
    } catch (err) {
      error.value = err.message || 'Failed to fetch benchmarks'
    } finally {
      loading.value = false
    }
  }

  async function fetchDistribution() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/admin/benchmark/distribution')
      distribution.value = data
    } catch (err) {
      error.value = err.message || 'Failed to fetch benchmark distribution'
    } finally {
      loading.value = false
    }
  }

  async function exportBenchmarks() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/admin/benchmark/export', { responseType: 'blob' })
      // Assuming the API returns a blob for download
      const url = window.URL.createObjectURL(new Blob([data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'benchmarks.csv')
      document.body.appendChild(link)
      link.click()
      link.parentNode?.removeChild(link)
    } catch (err) {
      error.value = err.message || 'Failed to export benchmarks'
    } finally {
      loading.value = false
    }
  }

  return {
    benchmarks,
    distribution,
    loading,
    error,
    fetchBenchmarks,
    fetchDistribution,
    exportBenchmarks
  }
})