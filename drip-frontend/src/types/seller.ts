export interface SellerProfile {
  id: string; user_id: string; brand_name: string; slug: string
  description: string | null; logo_url: string | null
  whatsapp_number: string; status: 'pending'|'active'|'suspended'
  slot_count: number; product_count: number
}
export interface SellerDashboard {
  gross_revenue: number; net_revenue: number; order_count: number
  product_count: number; avg_order_value: number; slot_count: number
  products_published: number
}
export interface WalletBalance {
  available_balance: number; pending_balance: number; total_earned: number
}
