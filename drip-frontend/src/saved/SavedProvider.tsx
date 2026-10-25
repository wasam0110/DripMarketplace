import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { Button, ErrorNotice } from '../components/ui'
import { changeSaved, readSaved, SAVED_KEY, writeSaved } from './storage'

interface SavedContext {
  ids: string[]; ready: boolean; error: unknown; notice: string
  set: (id: string, wanted: boolean) => void; reload: () => void; clear: () => boolean
}
const Context = createContext<SavedContext | null>(null)
export function SavedProvider({ children }: { children: ReactNode }) {
  const [ids, setIds] = useState<string[]>([])
  const [ready, setReady] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  function reload() {
    try { setIds(readSaved()); setError(null) }
    catch { setError(new Error('Saved pieces could not be read. Your stored list has not been overwritten. Retry or clear it from Saved pieces.')) }
    setReady(true)
  }
  useEffect(() => {
    reload()
    function changed(event: StorageEvent) {
      if (event.key === SAVED_KEY || event.key === null) { setNotice(''); reload() }
    }
    window.addEventListener('storage', changed)
    return () => window.removeEventListener('storage', changed)
  }, [])
  function set(id: string, wanted: boolean) {
    if (!ready || error) return
    try {
      // Re-read before writing so stale component state does not erase other tab edits.
      const next = changeSaved(readSaved(), id, wanted)
      writeSaved(next); setIds(next); setError(null)
      setNotice(wanted ? 'Saved on this device.' : 'Removed from saved pieces on this device.')
    } catch (reason) {
      setError(reason instanceof Error ? reason : new Error('Your browser could not save this change.'))
      setNotice('')
    }
  }
  function clear() {
    try { localStorage.removeItem(SAVED_KEY); setIds([]); setError(null); setNotice('Saved pieces cleared on this device.'); return true }
    catch { setError(new Error('Your browser could not clear saved pieces. Check site-storage permissions.')); return false }
  }
  return <Context.Provider value={{ ids, ready, error, notice, set, reload, clear }}>{children}</Context.Provider>
}
export function useSaved() {
  const value = useContext(Context)
  if (!value) throw new Error('Saved pieces require their provider.')
  return value
}
export function SaveButton({ id, name }: { id: string; name: string }) {
  const saved = useSaved()
  const active = saved.ids.includes(id.toLowerCase())
  return <Button className="button-secondary save-piece" disabled={!saved.ready || Boolean(saved.error)} aria-pressed={active}
    aria-label={active ? `Remove ${name} from saved pieces` : `Save ${name} on this device`}
    onClick={() => saved.set(id, !active)}>{active ? 'Saved on this device' : 'Save piece'}</Button>
}
export function SavedFeedback() {
  const saved = useSaved()
  return <>
    {Boolean(saved.error) && <div className="container saved-feedback"><ErrorNotice error={saved.error} /><Link className="text-link" to="/saved">Manage saved pieces</Link></div>}
    <div className="sr-only" aria-live="polite">{saved.notice}</div>
  </>
}
