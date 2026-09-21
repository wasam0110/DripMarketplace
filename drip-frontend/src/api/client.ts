import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { env } from '@/config/env'

let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

function subscribeToRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}
function onRefreshed(token: string) {
  refreshSubscribers.forEach(cb => cb(token))
  refreshSubscribers = []
}

// Lazy import to avoid circular dependency
function getAuthStore() {
  return import('@/store/authStore').then(m => m.useAuthStore)
}

export const client: AxiosInstance = axios.create({
  baseURL: `${env.apiUrl}/api/v1`,
  withCredentials: true,
  timeout: 10_000,
})

client.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const store = (await getAuthStore()).getState()
  if (store.accessToken) {
    config.headers.Authorization = `Bearer ${store.accessToken}`
  }
  config.headers['X-Request-ID'] = crypto.randomUUID()
  return config
})

client.interceptors.response.use(
  r => r,
  async error => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry && original.url !== '/auth/refresh') {
      if (isRefreshing) {
        return new Promise(resolve => {
          subscribeToRefresh(token => {
            original.headers.Authorization = `Bearer ${token}`
            resolve(client(original))
          })
        })
      }
      original._retry  = true
      isRefreshing     = true
      try {
        const { data } = await axios.post(
          `${env.apiUrl}/api/v1/auth/refresh`, {},
          { withCredentials: true }
        )
        const store = (await getAuthStore()).getState()
        store.setAccessToken(data.access_token)
        onRefreshed(data.access_token)
        original.headers.Authorization = `Bearer ${data.access_token}`
        return client(original)
      } catch {
        const store = (await getAuthStore()).getState()
        store.logout()
        window.location.href = '/login'
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)
