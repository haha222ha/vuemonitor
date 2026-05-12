import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/utils/api'

export const useAlertConfigStore = defineStore('alertConfig', () => {
  const rules = ref([])
  const channels = ref([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchRules() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/admin/alert-rules')
      rules.value = data.items || []
    } catch (err) {
      error.value = err.message || 'Failed to fetch alert rules'
    } finally {
      loading.value = false
    }
  }

  async function fetchChannels() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/admin/alert-channels')
      channels.value = data.items || []
    } catch (err) {
      error.value = err.message || 'Failed to fetch alert channels'
    } finally {
      loading.value = false
    }
  }

  async function createRule(data: Record<string, any>) {
    loading.value = true
    error.value = null
    try {
      await api.post('/admin/alert-rules', data)
      // Optionally refresh rules after creation
      // fetchRules()
    } catch (err) {
      error.value = err.message || 'Failed to create alert rule'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateRule(id: string, data: Record<string, any>) {
    loading.value = true
    error.value = null
    try {
      await api.put(`/admin/alert-rules/${id}`, data)
      // Optionally update the rule in the list
      const index = rules.value.findIndex(r => r.id === id)
      if (index !== -1) {
        rules.value[index] = { ...rules.value[index], ...data }
      }
    } catch (err) {
      error.value = err.message || 'Failed to update alert rule'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteRule(id: string) {
    loading.value = true
    error.value = null
    try {
      await api.delete(`/admin/alert-rules/${id}`)
      // Optionally remove the rule from the list
      const index = rules.value.findIndex(r => r.id === id)
      if (index !== -1) {
        rules.value.splice(index, 1)
      }
    } catch (err) {
      error.value = err.message || 'Failed to delete alert rule'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createChannel(data: Record<string, any>) {
    loading.value = true
    error.value = null
    try {
      await api.post('/admin/alert-channels', data)
      // Optionally refresh channels after creation
      // fetchChannels()
    } catch (err) {
      error.value = err.message || 'Failed to create alert channel'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateChannel(id: string, data: Record<string, any>) {
    loading.value = true
    error.value = null
    try {
      await api.put(`/admin/alert-channels/${id}`, data)
      // Optionally update the channel in the list
      const index = channels.value.findIndex(c => c.id === id)
      if (index !== -1) {
        channels.value[index] = { ...channels.value[index], ...data }
      }
    } catch (err) {
      error.value = err.message || 'Failed to update alert channel'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteChannel(id: string) {
    loading.value = true
    error.value = null
    try {
      await api.delete(`/admin/alert-channels/${id}`)
      // Optionally remove the channel from the list
      const index = channels.value.findIndex(c => c.id === id)
      if (index !== -1) {
        channels.value.splice(index, 1)
      }
    } catch (err) {
      error.value = err.message || 'Failed to delete alert channel'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function testChannel(id: string) {
    loading.value = true
    error.value = null
    try {
      await api.post(`/admin/alert-channels/${id}/test`)
    } catch (err) {
      error.value = err.message || 'Failed to test alert channel'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    rules,
    channels,
    loading,
    error,
    fetchRules,
    fetchChannels,
    createRule,
    updateRule,
    deleteRule,
    createChannel,
    updateChannel,
    deleteChannel,
    testChannel
  }
})