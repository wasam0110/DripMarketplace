import { useQuery } from '@tanstack/react-query'
import { adminApi } from '@/api/admin.api'
import { qk } from '@/api/queryKeys'
import { CODQueue } from '@/components/admin/CODQueue'

export default function AdminCODQueuePage() {
  const { data, isLoading, refetch } = useQuery({ queryKey: qk.admin.cod(), queryFn: adminApi.codQueue })
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">COD Queue</h1>
        {data?.data && <span className="text-muted text-sm">{data.data.length} pending</span>}
      </div>
      <div className="panel">
        {isLoading ? <p className="text-muted text-sm">Loading…</p> : <CODQueue orders={data?.data ?? []} onRefresh={refetch} />}
      </div>
    </div>
  )
}
