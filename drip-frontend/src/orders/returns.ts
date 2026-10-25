import { isOrderId, type OrderDetail } from './api'

export type ReturnPayload = { seller_order_id: string; reason: string; items: { order_item_id: string; quantity: number }[] }
export type ReturnReceipt = { id: string; order_id: string; seller_order_id: string; status: string; reason: string; items: { order_item_id: string; quantity: number }[] }

/** A return belongs to one brand shipment; purchased quantities are only upper bounds. */
export function returnPayload(order: OrderDetail, quantities: Record<string, number>, reason: string): ReturnPayload {
  if (!['delivered', 'completed'].includes(order.status)) throw new Error('Returns are available only for delivered or completed orders.')
  const trimmed = reason.trim()
  if (trimmed.length < 10 || trimmed.length > 1000) throw new Error('Give a return reason between 10 and 1,000 characters.')
  const ids = Object.keys(quantities)
  if (!ids.length) throw new Error('Select at least one piece to return.')
  const items = ids.map((id) => {
    const item = order.items.find((entry) => entry.id === id)
    if (!item || !isOrderId(id) || !Number.isInteger(quantities[id]) || quantities[id] < 1 || quantities[id] > item.quantity) throw new Error('Choose a valid purchased item and quantity.')
    return item
  })
  const shipments = order.seller_orders.filter((shipment) => shipment.seller_id === items[0].seller_id)
  if (items.some((item) => item.seller_id !== items[0].seller_id)) throw new Error('Choose pieces from one brand only. Submit separate requests for different brands.')
  if (shipments.length !== 1 || !isOrderId(shipments[0].id)) throw new Error('The brand shipment could not be identified. Refresh the order or contact support.')
  return { seller_order_id: shipments[0].id, reason: trimmed, items: items.map((item) => ({ order_item_id: item.id, quantity: quantities[item.id] })) }
}

/** Do not claim success when a write response belongs to another order or selection. */
export function confirmReturn(value: ReturnReceipt, orderId: string, payload: ReturnPayload): ReturnReceipt {
  if (!value || !isOrderId(value.id) || value.order_id !== orderId || value.seller_order_id !== payload.seller_order_id
    || value.status !== 'requested' || value.reason !== payload.reason || !Array.isArray(value.items)
    || value.items.length !== payload.items.length || new Set(value.items.map((item) => item?.order_item_id)).size !== payload.items.length
    || !payload.items.every((item) => value.items.some((returned) => returned?.order_item_id === item.order_item_id && returned.quantity === item.quantity))) {
    throw new Error('The return request could not be confirmed. Contact support before submitting it again.')
  }
  return value
}
