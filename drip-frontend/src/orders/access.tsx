import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from '../auth/AuthProvider'

interface GuestAccess { id: string; token: string }
const Context = createContext<{ access: GuestAccess | null; remember: (access: GuestAccess) => void } | null>(null)

/** A checkout-to-tracking handoff in memory only, isolated when the account changes. */
export function OrderAccessProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const owner = user?.id ?? 'guest'
  const [saved, setSaved] = useState<{ owner: string; access: GuestAccess } | null>(null)
  useEffect(() => { setSaved(null) }, [owner])
  return <Context.Provider value={{ access: saved?.owner === owner ? saved.access : null,
    remember: (access) => setSaved({ owner, access }),
  }}>{children}</Context.Provider>
}
export function useOrderAccess() {
  const value = useContext(Context)
  if (!value) throw new Error('Order access requires its provider.')
  return value
}
