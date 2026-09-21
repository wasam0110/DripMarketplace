export type OrderStatus = 'pending_cod_verification'|'processing'|'shipped'|'delivered'|'cancelled'|'return_requested'|'returned'
export type PaymentMethod = 'payfast'|'cod'
export interface OrderItem {
  id: string; product_name: string; variant_sku: string
  quantity: number; unit_price: number; subtotal: number; image_url: string | null
}
export interface ShippingAddress {
  recipient_name: string; phone: string; street: string; city: string; province: string
}
export interface Order {
  id: string; order_number: string; status: OrderStatus
  payment_method: PaymentMethod; items: OrderItem[]
  shipping_address: ShippingAddress; subtotal: number
  shipping_fee: number; discount: number; total: number
  created_at: string; updated_at: string
}
export interface CartItem {
  id: string; variant_id: string; product_id: string
  product_name: string; image_url: string | null
  size_value: string; colour: string; unit_price: number; quantity: number
}
