import { X, ShoppingBag, ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useCartStore } from '@/store/cartStore'
import { CartItem } from './CartItem'
import { pkr } from '@/utils/currency'

export function CartDrawer() {
  const { isOpen, closeCart, items, total } = useCartStore(s => ({
    isOpen:   s.isOpen,
    closeCart: s.closeCart,
    items:    s.items,
    total:    s.total(),
  }))

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm" onClick={closeCart} />
          <motion.aside
            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 z-50 w-full sm:w-[400px] bg-surface border-l border-border flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-sm tracking-wide">Your bag</h2>
                {items.length > 0 && (
                  <span className="bg-accent text-bg text-[10px] font-bold w-5 h-5 flex items-center justify-center">
                    {items.reduce((a,i) => a + i.quantity, 0)}
                  </span>
                )}
              </div>
              <button onClick={closeCart} className="text-muted hover:text-white"><X size={18} /></button>
            </div>

            {/* Items */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {items.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                  <ShoppingBag size={36} className="text-border" />
                  <p className="text-muted text-sm">Your bag is empty.</p>
                  <button onClick={closeCart} className="btn-outline text-xs">Keep shopping</button>
                </div>
              ) : (
                <div className="flex flex-col divide-y divide-border">
                  {items.map(item => <CartItem key={item.id} item={item} />)}
                </div>
              )}
            </div>

            {/* Footer */}
            {items.length > 0 && (
              <div className="border-t border-border px-6 py-4 flex flex-col gap-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Subtotal</span>
                  <span className="font-bold">{pkr(total)}</span>
                </div>
                <p className="text-[10px] text-muted">Shipping calculated at checkout.</p>
                <Link to="/checkout" onClick={closeCart} className="btn-primary justify-center w-full">
                  Checkout <ArrowUpRight size={15} />
                </Link>
              </div>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
