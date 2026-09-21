export const env = {
  apiUrl: (import.meta.env.VITE_API_URL as string || 'http://localhost:8000').replace(/\/$/, ''),
  isDev:  import.meta.env.DEV,
} as const
