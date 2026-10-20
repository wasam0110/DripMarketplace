import { useEffect, useState } from 'react'
import { request } from '../api/client'

/** Cancel stale requests when the route or filters change; expose an explicit retry. */
export function useResource<T>(path: string) {
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState<{ path: string; data: T | null; loading: boolean; error: unknown }>({
    path, data: null, loading: true, error: null,
  })
  useEffect(() => {
    const controller = new AbortController()
    setState({ path, data: null, loading: true, error: null })
    request<T>(path, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setState({ path, data, loading: false, error: null }) })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ path, data: null, loading: false, error })
      })
    return () => controller.abort()
  }, [path, attempt])
  return { ...(state.path === path ? state : { data: null, loading: true, error: null }), retry: () => setAttempt((value) => value + 1) }
}
