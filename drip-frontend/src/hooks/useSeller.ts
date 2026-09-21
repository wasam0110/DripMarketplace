import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { sellerApi } from '@/api/seller.api'
import { qk } from '@/api/queryKeys'

export function useSellerProfile() {
  return useQuery({ queryKey: qk.seller.profile(), queryFn: sellerApi.profile })
}
export function useSellerDashboard(period = 'month') {
  return useQuery({ queryKey: qk.seller.dashboard(period), queryFn: () => sellerApi.dashboard(period) })
}
export function useSellerWallet() {
  return useQuery({ queryKey: qk.seller.wallet(), queryFn: sellerApi.wallet })
}
export function useSellerProducts(filters = {}) {
  return useQuery({ queryKey: qk.seller.products(filters), queryFn: () => sellerApi.products(filters) })
}
export function useSellerInventory(filters = {}) {
  return useQuery({ queryKey: qk.seller.inventory(filters), queryFn: () => sellerApi.inventory(filters) })
}
export function useCreateProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: sellerApi.createProduct,
    onSuccess:  () => qc.invalidateQueries({ queryKey: qk.seller.products({}) }),
  })
}
export function useUpdateProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => sellerApi.updateProduct(id, data),
    onSuccess:  () => qc.invalidateQueries({ queryKey: qk.seller.products({}) }),
  })
}
