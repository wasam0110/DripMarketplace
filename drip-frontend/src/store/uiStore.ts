import { create } from 'zustand'

interface UIState {
  searchOpen:   boolean
  sidebarOpen:  boolean
  activeModal:  string | null
  openSearch:   () => void
  closeSearch:  () => void
  toggleSidebar:() => void
  openModal:    (id: string) => void
  closeModal:   () => void
}

export const useUIStore = create<UIState>()(set => ({
  searchOpen:    false,
  sidebarOpen:   false,
  activeModal:   null,
  openSearch:    () => set({ searchOpen: true }),
  closeSearch:   () => set({ searchOpen: false }),
  toggleSidebar: () => set(s => ({ sidebarOpen: !s.sidebarOpen })),
  openModal:     (id) => set({ activeModal: id }),
  closeModal:    () => set({ activeModal: null }),
}))
