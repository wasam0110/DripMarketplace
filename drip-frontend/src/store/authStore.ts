import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types/user'

interface AuthState {
  accessToken: string | null
  user: User | null
  setAccessToken: (t: string) => void
  setUser: (u: User) => void
  setAuth: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user:        null,
      setAccessToken: (accessToken) => set({ accessToken }),
      setUser:        (user)        => set({ user }),
      setAuth:        (accessToken, user) => set({ accessToken, user }),
      logout:         ()            => set({ accessToken: null, user: null }),
    }),
    {
      name:       'drip-auth',
      partialize: (s) => ({ user: s.user }),
      // accessToken lives in memory only — not persisted
    }
  )
)
