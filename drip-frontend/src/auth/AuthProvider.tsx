import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { ApiError, refreshSession, request, setAccessToken } from '../api/client'
import type { AuthResponse, User } from '../api/types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  error: string | null
  signIn: (email: string, password: string, totp?: string) => Promise<void>
  signOut: () => Promise<void>
  acceptSession: (session: AuthResponse) => void
  clearSession: () => void
  updateProfileNames: (profile: Pick<User, 'id' | 'first_name' | 'last_name'>) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    refreshSession()
      .then(() => request<User>('/auth/me', { authenticated: true }))
      .then((profile) => { if (active) setUser(profile) })
      .catch((reason: unknown) => {
        if (active && !(reason instanceof ApiError && reason.status === 401)) {
          setError('We couldn’t restore your session. You can try signing in again.')
        }
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  async function signIn(email: string, password: string, totp?: string) {
    const result = await request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password, ...(totp ? { totp_code: totp } : {}) }),
    })
    acceptSession(result)
  }

  function acceptSession(session: AuthResponse) {
    setAccessToken(session.access_token)
    setUser(session.user)
    setError(null)
  }

  function clearSession() {
    setAccessToken(null)
    setUser(null)
    setError(null)
  }

  async function signOut() {
    // Do not claim server-side revocation succeeded if the network request fails.
    // Rotate first so an expired access token cannot prevent a valid session's logout.
    await refreshSession()
    await request('/auth/logout', { method: 'POST', authenticated: true })
    clearSession()
  }

  function updateProfileNames(profile: Pick<User, 'id' | 'first_name' | 'last_name'>) {
    setUser((current) => current?.id === profile.id ? { ...current, first_name: profile.first_name, last_name: profile.last_name } : current)
  }

  return <AuthContext.Provider value={{ user, loading, error, signIn, signOut, acceptSession, clearSession, updateProfileNames }}>
    {children}
  </AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
