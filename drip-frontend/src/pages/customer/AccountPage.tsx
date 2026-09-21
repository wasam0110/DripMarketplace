import { Routes, Route, NavLink, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useLogout } from '@/hooks/useAuth'
import { useOrders } from '@/hooks/useOrders'
import { pkr } from '@/utils/currency'
import { Badge } from '@/components/ui/Badge'
import { LogOut } from 'lucide-react'

function AccountNav() {
  const logout = useLogout()
  const links  = [
    { to: '/account',          label: 'Overview', end: true },
    { to: '/account/orders',   label: 'Orders' },
    { to: '/account/wishlist', label: 'Wishlist' },
    { to: '/account/settings', label: 'Settings' },
  ]
  return (
    <aside className="flex flex-col gap-1 shrink-0 w-44">
      {links.map(l => (
        <NavLink key={l.to} to={l.to} end={l.end}
          className={({ isActive }) => `text-sm px-3 py-2 transition-colors ${isActive ? 'text-accent font-bold' : 'text-muted hover:text-white'}`}>
          {l.label}
        </NavLink>
      ))}
      <button onClick={() => logout.mutate()}
        className="flex items-center gap-2 text-sm text-muted hover:text-danger px-3 py-2 transition-colors mt-4">
        <LogOut size={14} />Sign out
      </button>
    </aside>
  )
}

function Overview() {
  const user = useAuthStore(s => s.user)
  const { data } = useOrders({ page: 1, per_page: 5 })
  return (
    <div className="flex flex-col gap-6">
      <div><h1 className="text-2xl font-bold">Welcome, {user?.first_name || 'back'}.</h1><p className="text-muted text-sm mt-1">{user?.email}</p></div>
      <div className="panel flex flex-col gap-3">
        <p className="text-[10px] font-bold tracking-widest text-muted">RECENT ORDERS</p>
        {data?.data.slice(0, 5).map(o => (
          <div key={o.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
            <div><p className="text-sm font-mono text-accent">#{o.order_number}</p><p className="text-xs text-muted">{new Date(o.created_at).toLocaleDateString()}</p></div>
            <div className="text-right"><p className="text-sm font-bold">{pkr(o.total)}</p><Badge label={o.status.replace(/_/g,' ').toUpperCase()} variant="muted" /></div>
          </div>
        ))}
        {!data?.data.length && <p className="text-muted text-sm py-4">No orders yet.</p>}
      </div>
    </div>
  )
}

function OrderHistory() {
  const { data, isLoading } = useOrders({ page: 1 })
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-bold">Orders</h2>
      {isLoading ? <p className="text-muted text-sm">Loading…</p> : data?.data.map(o => (
        <div key={o.id} className="panel flex items-center justify-between">
          <div><p className="font-mono text-sm text-accent">#{o.order_number}</p><p className="text-xs text-muted">{new Date(o.created_at).toLocaleDateString()} · {o.payment_method}</p></div>
          <div className="text-right"><p className="font-bold">{pkr(o.total)}</p><Badge label={o.status.replace(/_/g,' ').toUpperCase()} variant="muted" /></div>
        </div>
      ))}
    </div>
  )
}

export default function AccountPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10 flex gap-10">
      <AccountNav />
      <div className="flex-1 min-w-0">
        <Routes>
          <Route index element={<Overview />} />
          <Route path="orders" element={<OrderHistory />} />
          <Route path="wishlist" element={<p className="text-muted">Wishlist coming soon.</p>} />
          <Route path="settings" element={<p className="text-muted">Settings coming soon.</p>} />
        </Routes>
      </div>
    </div>
  )
}
