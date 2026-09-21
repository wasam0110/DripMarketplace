import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cartApi, orderApi } from '@/api/order.api'
import { useCartStore } from '@/store/cartStore'
import { qk } from '@/api/queryKeys'

export function useCart() {
  return useQuery({ queryKey: qk.cart.all(), queryFn: cartApi.get, staleTime: 30_000 })
}
export function useOrders(filters = {}) {
  return useQuery({ queryKey: qk.orders.list(filters), queryFn: () => orderApi.list(filters) })
}
export function useOrder(id?: string) {
  return useQuery({
    queryKey: qk.orders.detail(id!),
    queryFn:  () => orderApi.detail(id!),
    enabled:  !!id,
  })
}
export function usePlaceOrder() {
  const clearCart = useCartStore(s => s.clearCart)
  const qc        = useQueryClient()
  return useMutation({
    mutationFn: orderApi.create,
    onSuccess:  () => { clearCart(); qc.invalidateQueries({ queryKey: ['orders'] }) },
  })
}
