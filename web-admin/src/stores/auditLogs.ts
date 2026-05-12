import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/utils/api'

export const useAuditLogsStore = defineStore('auditLogs', () => {
  const logs = ref([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchLogs(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/admin/audit-logs', { params })
      logs.value = data.items || []
      total.value = data.total || 0
    } catch (err) {
      error.value = err.message || 'Failed to fetch audit logs'
    } finally {
      loading.value = false
    }
  }

  return {
    logs,
    total,
    loading,
    error,
    fetchLogs
  }
})