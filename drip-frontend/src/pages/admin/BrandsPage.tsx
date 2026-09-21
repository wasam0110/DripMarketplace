import { useQuery } from '@tanstack/react-query'
import { adminApi } from '@/api/admin.api'
import { qk } from '@/api/queryKeys'
import { BrandTable } from '@/components/admin/BrandTable'

export default function AdminBrandsPage() {
  const { data, isLoading, refetch } = useQuery({ queryKey: qk.admin.sellers({}), queryFn: () => adminApi.sellers() })
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Brands</h1>
      <div className="panel"><BrandTable brands={data?.data ?? []} onRefresh={refetch} /></div>
    </div>
  )
}
