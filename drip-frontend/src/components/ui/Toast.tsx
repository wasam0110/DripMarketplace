import { create } from 'zustand'
import { useEffect } from 'react'
import { CheckCircle2, XCircle, AlertCircle, X } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'

interface Toast { id: string; message: string; type: 'success' | 'error' | 'info' }
interface ToastState { toasts: Toast[]; push: (t: Omit<Toast, 'id'>) => void; remove: (id: string) => void }

export const useToastStore = create<ToastState>()(set => ({
  toasts: [],
  push:   (t)  => set(s => ({ toasts: [...s.toasts, { ...t, id: crypto.randomUUID() }] })),
  remove: (id) => set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })),
}))

export const toast = {
  success: (message: string) => useToastStore.getState().push({ message, type: 'success' }),
  error:   (message: string) => useToastStore.getState().push({ message, type: 'error' }),
  info:    (message: string) => useToastStore.getState().push({ message, type: 'info' }),
}

const icons = { success: CheckCircle2, error: XCircle, info: AlertCircle }
const colors = { success: 'text-success', error: 'text-danger', info: 'text-accent' }

function ToastItem({ t }: { t: Toast }) {
  const remove = useToastStore(s => s.remove)
  useEffect(() => { const tid = setTimeout(() => remove(t.id), 4000); return () => clearTimeout(tid) }, [t.id, remove])
  const Icon = icons[t.type]
  return (
    <motion.div
      initial={{ opacity: 0, x: 48 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 48 }}
      className="flex items-start gap-3 bg-surface border border-border px-4 py-3 min-w-[280px] max-w-sm shadow-2xl"
    >
      <Icon size={16} className={`mt-0.5 shrink-0 ${colors[t.type]}`} />
      <p className="text-sm text-white flex-1">{t.message}</p>
      <button onClick={() => remove(t.id)} className="text-muted hover:text-white shrink-0"><X size={14} /></button>
    </motion.div>
  )
}

export function ToastContainer() {
  const toasts = useToastStore(s => s.toasts)
  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2">
      <AnimatePresence>{toasts.map(t => <ToastItem key={t.id} t={t} />)}</AnimatePresence>
    </div>
  )
}
