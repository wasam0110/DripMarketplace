import { useQuery } from '@tanstack/react-query'
import { adminApi } from '@/api/admin.api'
import { qk } from '@/api/queryKeys'
import { PayoutQueue } from '@/components/admin/PayoutQueue'

export default function AdminPayoutsPage() {
  const { data, isLoading, refetch } = useQuery({ queryKey: qk.admin.payouts({}), queryFn: () => adminApi.payouts() })
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Payouts</h1>
      <div className="panel">
        {isLoading ? <p className="text-muted text-sm">Loading…</p> : <PayoutQueue payouts={data?.data ?? []} onRefresh={refetch} />}
      </div>
    </div>
  )
}
