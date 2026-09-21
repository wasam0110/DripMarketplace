import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { CartItem } from '@/types/order'
import type { Product, ProductVariant } from '@/types/product'

interface CartState {
  items:     CartItem[]
  isOpen:    boolean
  addItem:   (variant: ProductVariant, product: Product, qty?: number) => void
  removeItem:(variantId: string) => void
  updateQty: (variantId: string, qty: number) => void
  clearCart: () => void
  openCart:  () => void
  closeCart: () => void
  total:     () => number
  count:     () => number
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items:  [],
      isOpen: false,
      addItem: (variant, product, qty = 1) => set(s => {
        const existing = s.items.find(i => i.variant_id === variant.id)
        if (existing) {
          return { items: s.items.map(i =>
            i.variant_id === variant.id ? { ...i, quantity: i.quantity + qty } : i
          )}
        }
        const item: CartItem = {
          id:           crypto.randomUUID(),
          variant_id:   variant.id,
          product_id:   product.id,
          product_name: product.name,
          image_url:    product.primary_image,
          size_value:   variant.size_value,
          colour:       variant.colour,
          unit_price:   variant.effective_price,
          quantity:     qty,
        }
        return { items: [...s.items, item], isOpen: true }
      }),
      removeItem: (variantId) => set(s => ({ items: s.items.filter(i => i.variant_id !== variantId) })),
      updateQty:  (variantId, qty) => set(s => ({
        items: qty <= 0
          ? s.items.filter(i => i.variant_id !== variantId)
          : s.items.map(i => i.variant_id === variantId ? { ...i, quantity: qty } : i),
      })),
      clearCart:  () => set({ items: [] }),
      openCart:   () => set({ isOpen: true }),
      closeCart:  () => set({ isOpen: false }),
      total:      () => get().items.reduce((a, i) => a + i.unit_price * i.quantity, 0),
      count:      () => get().items.reduce((a, i) => a + i.quantity, 0),
    }),
    { name: 'drip-cart', partialize: s => ({ items: s.items }) }
  )
)
