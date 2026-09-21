import { useQuery } from '@tanstack/react-query'
import { sellerApi } from '@/api/seller.api'
import { OrderTable } from '@/components/seller/OrderTable'
import { qk } from '@/api/queryKeys'

export default function SellerOrdersPage() {
  const { data, isLoading } = useQuery({ queryKey: qk.seller.orders({}), queryFn: () => sellerApi.orders() })
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Orders</h1>
      <div className="panel">
        <OrderTable orders={data?.data ?? []} loading={isLoading} />
      </div>
    </div>
  )
}
