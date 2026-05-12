import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/utils/api'

export const useCollectStore = defineStore('collect', () => {
  const tasks = ref([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchTasks(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/admin/collect/tasks', { params })
      tasks.value = data.items || []
      total.value = data.total || 0
    } catch (err) {
      error.value = err.message || 'Failed to fetch tasks'
    } finally {
      loading.value = false
    }
  }

  async function cancelTask(id: string) {
    loading.value = true
    error.value = null
    try {
      await api.put(`/admin/collect/tasks/${id}/cancel`)
      // Optionally update the task status in the list
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tasks.value[index].status = 'cancelled'
      }
    } catch (err) {
      error.value = err.message || 'Failed to cancel task'
    } finally {
      loading.value = false
    }
  }

  async function createTask(data: Record<string, any>) {
    loading.value = true
    error.value = null
    try {
      const { data: responseData } = await api.post('/admin/collect/tasks', data)
      // Optionally add the new task to the list if needed
      tasks.value.push(responseData)
      return responseData
    } catch (err) {
      error.value = err.message || 'Failed to create task'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    tasks,
    total,
    loading,
    error,
    fetchTasks,
    cancelTask,
    createTask
  }
})