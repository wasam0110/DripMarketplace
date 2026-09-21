import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { productApi, type ProductFilters } from '@/api/product.api'
import { qk } from '@/api/queryKeys'

export function useProducts(filters: ProductFilters = {}) {
  return useInfiniteQuery({
    queryKey:      qk.products.list(filters),
    queryFn:       ({ pageParam }) => productApi.list({ ...filters, cursor: pageParam as string | undefined }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: page => page.next_cursor ?? undefined,
    staleTime:     60_000,
  })
}

export function useProduct(id?: string) {
  return useQuery({
    queryKey: qk.products.detail(id!),
    queryFn:  () => productApi.detail(id!),
    enabled:  !!id,
  })
}

export function useProductBySlug(slug?: string) {
  return useQuery({
    queryKey: [...qk.products.all(), 'slug', slug],
    queryFn:  () => productApi.bySlug(slug!),
    enabled:  !!slug,
  })
}

export function useProductReviews(productId?: string) {
  return useQuery({
    queryKey: qk.products.reviews(productId!),
    queryFn:  () => productApi.reviews(productId!),
    enabled:  !!productId,
  })
}
