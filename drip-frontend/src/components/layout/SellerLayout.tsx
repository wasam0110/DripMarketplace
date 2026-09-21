import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Package, ShoppingBag, Wallet, Settings, LogOut, ChevronRight } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useLogout } from '@/hooks/useAuth'
import { ToastContainer } from '@/components/ui/Toast'

const NAV = [
  { to: '/dashboard',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/dashboard/products', icon: Package,          label: 'Products' },
  { to: '/dashboard/orders',   icon: ShoppingBag,      label: 'Orders' },
  { to: '/dashboard/wallet',   icon: Wallet,           label: 'Wallet' },
  { to: '/dashboard/settings', icon: Settings,         label: 'Settings' },
]

export function SellerLayout() {
  const user   = useAuthStore(s => s.user)
  const logout = useLogout()

  return (
    <div className="min-h-screen flex bg-bg text-white">
      {/* Sidebar */}
      <aside className="w-56 border-r border-border flex flex-col shrink-0">
        <div className="h-14 border-b border-border flex items-center px-5">
          <span className="font-mono font-bold text-lg">DRIP<span className="text-accent">.</span></span>
          <span className="ml-2 text-[10px] text-muted font-mono">SELLER</span>
        </div>
        <nav className="flex-1 py-4">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={to === '/dashboard'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${isActive ? 'text-accent' : 'text-muted hover:text-white'}`
              }>
              <Icon size={16} />{label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-border p-4">
          <p className="text-xs text-muted truncate mb-3">{user?.email}</p>
          <button onClick={() => logout.mutate()} className="flex items-center gap-2 text-xs text-muted hover:text-danger transition-colors">
            <LogOut size={14} />Sign out
          </button>
        </div>
      </aside>

      {/* Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 p-8 overflow-auto"><Outlet /></div>
      </div>
      <ToastContainer />
    </div>
  )
}
