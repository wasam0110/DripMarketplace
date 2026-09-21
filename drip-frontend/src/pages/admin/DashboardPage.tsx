import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, ShoppingBag, Store, Banknote } from 'lucide-react'
import { adminApi } from '@/api/admin.api'
import { qk } from '@/api/queryKeys'
import { KPICard } from '@/components/admin/KPICard'
import { pkr } from '@/utils/currency'

export default function AdminDashboardPage() {
  const [period, setPeriod] = useState('month')
  const { data, isLoading } = useQuery({ queryKey: qk.admin.dashboard(period), queryFn: () => adminApi.dashboard(period) })

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-mono tracking-widest text-danger mb-1">CONTROL ROOM</p>
          <h1 className="text-2xl font-bold">Admin dashboard</h1>
        </div>
        <select value={period} onChange={e => setPeriod(e.target.value)}
          className="bg-surface border border-border text-xs px-3 py-2 focus:outline-none focus:border-accent">
          <option value="week">This week</option>
          <option value="month">This month</option>
          <option value="year">This year</option>
        </select>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="GMV"             value={isLoading ? '…' : pkr(data?.total_gmv ?? 0)}          icon={<TrendingUp size={16} />} accent />
        <KPICard label="Platform revenue" value={isLoading ? '…' : pkr(data?.platform_revenue ?? 0)}  icon={<Banknote size={16} />} />
        <KPICard label="Orders"          value={isLoading ? '…' : data?.total_orders ?? 0}             icon={<ShoppingBag size={16} />} />
        <KPICard label="Pending payouts" value={isLoading ? '…' : pkr(data?.pending_payouts ?? 0)}    icon={<Store size={16} />} />
      </div>
    </div>
  )
}
