import { useEffect, useState } from 'react'
import { request } from '../api/client'
import { paisa } from '../checkout/preview'

export interface OrderRow {
  id: string; order_number: string; status: string; total: string; item_count: number; created_at: string
}
export interface OrderList {
  data: OrderRow[]
  pagination: { page: number; per_page: number; total: number; total_pages: number }
}
export interface OrderItem {
  id: string; seller_id: string; product_id: string; variant_id: string
  product_name: string; variant_label: string; unit_price: string; quantity: number; subtotal: string
}
export interface Shipment {
  id: string; seller_id: string; brand_name: string; status: string; subtotal: string
  tracking_number: string | null; courier_name: string | null; shipped_at: string | null; delivered_at: string | null
}
export interface OrderDetail {
  id: string; order_number: string; status: string; payment_method: string; created_at: string
  subtotal: string; discount_amount: string; shipping_fee: string; total: string; notes: string | null
  address: { recipient_name: string; phone: string; street: string; city: string; province: string; note: string | null } | null
  items: OrderItem[]; seller_orders: Shipment[]
}
export const isOrderId = (id: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
export function orderPath(identifier: string) {
  const value = identifier.trim()
  if (!value || value.length > 100 || /[\x00-\x1f\x7f]/.test(value)) throw new Error('Enter a valid order number.')
  return `/orders/${isOrderId(value) ? '' : 'number/'}${encodeURIComponent(value)}`
}
function requireValue(valid: unknown): asserts valid {
  if (!valid) throw new Error('The server returned incomplete order information. Please retry.')
}
const text = (value: unknown) => typeof value === 'string' && value.length > 0
const integer = (value: unknown, minimum: number) => Number.isSafeInteger(value) && (value as number) >= minimum
export function validateOrders(value: OrderList): OrderList {
  requireValue(value && Array.isArray(value.data) && value.pagination)
  const page = value.pagination
  requireValue(integer(page.page, 1) && integer(page.per_page, 1) && integer(page.total, 0) && integer(page.total_pages, 1))
  value.data.forEach((row) => {
    requireValue(row && isOrderId(row.id) && text(row.order_number) && text(row.status) && integer(row.item_count, 0) && text(row.created_at))
    paisa(row.total)
  })
  return value
}
export function validateOrderDetail(value: OrderDetail): OrderDetail {
  requireValue(value && isOrderId(value.id) && text(value.order_number) && text(value.status) && text(value.payment_method) && text(value.created_at))
  requireValue(Array.isArray(value.items) && Array.isArray(value.seller_orders))
  requireValue(value.notes === null || typeof value.notes === 'string')
  for (const amount of [value.subtotal, value.discount_amount, value.shipping_fee, value.total]) paisa(amount)
  requireValue(paisa(value.subtotal) - paisa(value.discount_amount) + paisa(value.shipping_fee) === paisa(value.total))
  value.items.forEach((item) => {
    requireValue(item && text(item.id) && text(item.seller_id) && text(item.product_name) && typeof item.variant_label === 'string' && integer(item.quantity, 1))
    paisa(item.subtotal); paisa(item.unit_price)
  })
  value.seller_orders.forEach((shipment) => {
    requireValue(shipment && text(shipment.id) && text(shipment.seller_id) && text(shipment.brand_name) && text(shipment.status))
    for (const field of ['tracking_number', 'courier_name', 'shipped_at', 'delivered_at'] as const) {
      requireValue(shipment[field] === null || typeof shipment[field] === 'string')
    }
    paisa(shipment.subtotal)
  })
  if (value.address !== null) {
    requireValue(value.address && ['recipient_name', 'phone', 'street', 'city', 'province'].every((field) => text(value.address![field as keyof NonNullable<OrderDetail['address']>])))
    requireValue(value.address.note === null || typeof value.address.note === 'string')
  }
  return value
}
const labels: Record<string, string> = {
  pending: 'Awaiting fulfilment', pending_payment: 'Awaiting payment', payment_confirmed: 'Payment confirmed',
  pending_cod_verification: 'Awaiting COD verification', processing: 'Preparing your order', shipped: 'Shipped',
  delivered: 'Delivered', completed: 'Completed', cancelled: 'Cancelled', refunded: 'Refunded', returned: 'Returned',
}
export const statusLabel = (status: string) => labels[status] ?? 'Status unavailable'
export function orderDate(date: string) {
  const value = new Date(date)
  return Number.isNaN(value.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat('en-PK', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Karachi' }).format(value)
}

/** Protected reads are scoped to mounted owner/credential components, never a shared cache. */
export function useOrderRead<T>(path: string, authenticated: boolean, validate: (data: T) => T, token?: string) {
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState<{ path: string; data: T | null; loading: boolean; error: unknown }>({ path, data: null, loading: true, error: null })
  useEffect(() => {
    const controller = new AbortController()
    setState({ path, data: null, loading: true, error: null })
    void request<T>(path, { authenticated, cache: 'no-store',
      signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
      headers: token ? { 'X-Guest-Token': token } : undefined,
    }).then(validate).then((data) => {
      if (!controller.signal.aborted) setState({ path, data, loading: false, error: null })
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ path, data: null, loading: false, error })
    })
    return () => controller.abort()
  }, [path, authenticated, validate, token, attempt])
  return { ...(state.path === path ? state : { data: null, loading: true, error: null }), retry: () => setAttempt((current) => current + 1) }
}
