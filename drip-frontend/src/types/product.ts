export interface Category { id: string; name: string; slug: string; parent_id: string | null }
export interface ProductVariant {
  id: string; sku: string; size_type: 'alpha' | 'numeric' | 'one_size'
  size_value: string; colour: string; is_active: boolean
  effective_price: number; stock: number
}
export interface ProductImage { id: string; url: string; sort_order: number }
export interface ProductSeller { id: string; brand_name: string; slug: string; logo_url: string | null }
export interface Product {
  id: string; name: string; slug: string; description: string | null
  price: number; sale_price: number | null; is_published: boolean
  avg_rating: number; review_count: number; primary_image: string | null
  images: ProductImage[]; variants: ProductVariant[]
  seller: ProductSeller; category: Category | null
  badge?: string; has_stock: boolean
}
export interface ProductListItem {
  id: string; name: string; slug: string; price: number; sale_price: number | null
  primary_image: string | null; avg_rating: number; review_count: number
  seller: ProductSeller; has_stock: boolean; badge?: string
}
export interface Review {
  id: string; rating: number; title: string | null; body: string | null
  status: string; is_verified_purchase: boolean
  helpful_count: number; unhelpful_count: number
  user: { id: string; first_name: string | null; avatar_url: string | null }
  created_at: string
}
