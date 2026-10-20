// Names and money units follow the running backend's OpenAPI contract.
export interface User {
  id: string
  email: string
  role: string
  first_name: string | null
  last_name: string | null
  has_verified_email: boolean
}

export interface AuthResponse { access_token: string; user: User }

export interface Product {
  id: string
  slug: string
  name: string
  brand_name: string
  price: string
  sale_price: string | null
  primary_image: string | null
  has_stock: boolean
}

export interface ProductVariant {
  id: string
  sku: string
  size_type: string
  size_value: string
  colour: string
  price: string
  stock: number
  available_stock: number
  is_active: boolean
}

export interface ProductDetail extends Product {
  description: string | null
  avg_rating: number
  review_count: number
  images: { id: string; url: string; alt_text: string | null; sort_order: number; is_primary: boolean }[]
  variants: ProductVariant[]
  seller: { id: string; slug: string; brand_name: string; return_policy: string | null }
}

export interface CartItem {
  variant_id: string
  product_id: string
  product_name: string
  brand_name: string
  brand_color: string
  primary_image: string | null
  size: string
  colour: string
  unit_price: string
  quantity: number
  subtotal: string
  available_stock: number
  seller_id: string
}

export interface Cart {
  items: CartItem[]
  item_count: number
  subtotal: string
  shipping_fee: string
  total: string
}

export interface CataloguePage {
  data: Product[]
  pagination: { next_cursor: string | null; has_next: boolean; limit: number }
}

export interface Brand {
  id: string
  slug: string
  brand_name: string
  description: string | null
  logo_url: string | null
  return_policy: string | null
}

export interface BrandsPage {
  data: Brand[]
  pagination: { page: number; per_page: number; total: number }
}

export function formatPrice(majorUnits: string): string {
  const value = Number(majorUnits)
  return Number.isFinite(value)
    ? `PKR ${new Intl.NumberFormat('en-PK', { maximumFractionDigits: 2 }).format(value)}`
    : 'Price unavailable'
}
