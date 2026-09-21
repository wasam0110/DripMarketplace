import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ShoppingBag, UserRound, Search, Menu, X } from 'lucide-react'
import { useCartStore } from '@/store/cartStore'
import { useAuthStore } from '@/store/authStore'
import { useUIStore } from '@/store/uiStore'

const NAV = [
  { label: 'Shop',      to: '/shop' },
  { label: 'Tops',      to: '/shop?category=tops' },
  { label: 'Bottoms',   to: '/shop?category=bottoms' },
  { label: 'Outerwear', to: '/shop?category=outerwear' },
  { label: 'Sell on DRIP', to: '/sell' },
]

export function Header() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const count    = useCartStore(s => s.count())
  const openCart = useCartStore(s => s.openCart)
  const user     = useAuthStore(s => s.user)
  const navigate = useNavigate()

  function handleAccount() {
    if (!user) navigate('/login')
    else if (user.role === 'admin')  navigate('/admin')
    else if (user.role === 'seller') navigate('/dashboard')
    else navigate('/account')
  }

  return (
    <>
      {/* Ticker */}
      <div className="bg-accent text-bg text-[10px] font-mono font-bold tracking-widest py-1.5 overflow-hidden">
        <div className="flex gap-16 animate-[ticker_20s_linear_infinite]">
          {['DRIP DROP 01 — FREE SHIPPING OVER PKR 10,000', 'SELL YOUR CULTURE / KEEP 85%', 'NEW IN EVERY FRIDAY', 'AUTHENTIC INDEPENDENT LABELS'].map((t, i) => (
            <span key={i} className="whitespace-nowrap">{t}</span>
          ))}
        </div>
      </div>

      <header className="sticky top-0 z-40 bg-bg/90 backdrop-blur border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
          {/* Mobile menu toggle */}
          <button className="sm:hidden text-muted hover:text-white" onClick={() => setMobileOpen(o => !o)}>
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>

          {/* Logo */}
          <Link to="/" className="font-mono font-bold text-xl tracking-tighter">
            DRIP<span className="text-accent">.</span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden sm:flex items-center gap-6">
            {NAV.map(n => (
              <Link key={n.to} to={n.to} className="text-xs font-bold tracking-widest text-muted hover:text-white transition-colors uppercase">
                {n.label}
              </Link>
            ))}
          </nav>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <button onClick={handleAccount} className="text-muted hover:text-white transition-colors"><UserRound size={19} /></button>
            <button onClick={openCart} className="relative text-muted hover:text-white transition-colors">
              <ShoppingBag size={19} />
              {count > 0 && (
                <span className="absolute -top-1 -right-1 bg-accent text-bg text-[9px] font-bold w-4 h-4 flex items-center justify-center">
                  {count}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Mobile Nav */}
        {mobileOpen && (
          <nav className="sm:hidden border-t border-border bg-surface px-4 py-4 flex flex-col gap-4">
            {NAV.map(n => (
              <Link key={n.to} to={n.to} onClick={() => setMobileOpen(false)}
                className="text-sm font-bold tracking-widest text-muted hover:text-white uppercase">
                {n.label}
              </Link>
            ))}
          </nav>
        )}
      </header>
    </>
  )
}
