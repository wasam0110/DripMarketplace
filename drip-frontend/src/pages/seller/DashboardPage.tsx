import { useState } from 'react'
import { LayoutDashboard, TrendingUp, Package, Wallet } from 'lucide-react'
import { useSellerDashboard, useSellerWallet } from '@/hooks/useSeller'
import { KPICard } from '@/components/admin/KPICard'
import { SlotMeter } from '@/components/seller/SlotMeter'
import { WalletCard } from '@/components/seller/WalletCard'
import { pkr } from '@/utils/currency'

export default function SellerDashboardPage() {
  const [period, setPeriod] = useState('month')
  const { data: dash, isLoading } = useSellerDashboard(period)
  const { data: wallet } = useSellerWallet()

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <select value={period} onChange={e => setPeriod(e.target.value)}
          className="bg-surface border border-border text-xs px-3 py-2 focus:outline-none focus:border-accent">
          <option value="week">This week</option>
          <option value="month">This month</option>
          <option value="year">This year</option>
        </select>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Gross revenue"  value={isLoading ? '…' : pkr(dash?.gross_revenue ?? 0)}  icon={<TrendingUp size={16} />} accent />
        <KPICard label="Net revenue"    value={isLoading ? '…' : pkr(dash?.net_revenue ?? 0)}     icon={<Wallet size={16} />} />
        <KPICard label="Orders"         value={isLoading ? '…' : dash?.order_count ?? 0}           icon={<Package size={16} />} />
        <KPICard label="Products live"  value={isLoading ? '…' : dash?.products_published ?? 0}    icon={<LayoutDashboard size={16} />} />
      </div>

      <div className="grid sm:grid-cols-2 gap-6">
        {dash && <SlotMeter used={dash.products_published} total={dash.slot_count} />}
        {wallet && <WalletCard wallet={wallet} />}
      </div>
    </div>
  )
}
