/**
 * Axios instance with auth/project interceptors.
 * Ported from autosre/lib/services/api_client.dart
 */
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'
import { useProjectStore } from '../stores/projectStore'

const apiClient = axios.create({
  baseURL: '',
  withCredentials: true,
  timeout: 30_000,
})

// Request interceptor: attach auth token and project ID headers
apiClient.interceptors.request.use((config) => {
  const { accessToken, isGuest } = useAuthStore.getState()
  const { projectId } = useProjectStore.getState()

  if (isGuest) {
    config.headers['X-Guest-Mode'] = 'true'
    config.headers['Authorization'] = 'Bearer dev-mode-bypass-token'
  } else if (accessToken) {
    config.headers['Authorization'] = `Bearer ${accessToken}`
  }

  if (projectId) {
    config.headers['X-GCP-Project-ID'] = projectId
  }

  return config
})

// Response interceptor: handle 401 → logout
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const { isGuest } = useAuthStore.getState()
      if (!isGuest) {
        useAuthStore.getState().logout()
      }
    }
    return Promise.reject(error)
  },
)

export default apiClient
