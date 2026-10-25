import { isOrderId } from './api'

export interface ReturnRow {
  id: string; order_id: string; seller_order_id: string; status: string; reason: string
  item_count: number; requested_at: string; resolved_at: string | null
}
export interface ReturnDetail extends ReturnRow {
  notes: string | null
  items: { id: string; order_item_id: string; quantity: number; reason: string | null }[]
}
export interface ReturnList { data: ReturnRow[]; total: number; page: number; total_pages: number }
const nullableText = (value: unknown) => value === null || typeof value === 'string'
const date = (value: unknown) => typeof value === 'string' && Number.isFinite(Date.parse(value))
function requireValid(value: unknown): asserts value {
  if (!value) throw new Error('The server returned incomplete return details. Please refresh or contact support.')
}
export function validateReturnRow(value: ReturnRow): ReturnRow {
  requireValid(value && isOrderId(value.id) && isOrderId(value.order_id) && isOrderId(value.seller_order_id)
    && typeof value.status === 'string' && value.status.length > 0 && typeof value.reason === 'string'
    && Number.isInteger(value.item_count) && value.item_count >= 1 && date(value.requested_at)
    && (value.resolved_at === null || date(value.resolved_at)))
  return value
}
export function validateReturnDetail(value: ReturnDetail, id: string): ReturnDetail {
  validateReturnRow(value)
  requireValid(value.id === id && nullableText(value.notes) && Array.isArray(value.items) && value.items.length === value.item_count)
  const ids = new Set<string>()
  for (const item of value.items) {
    requireValid(item && isOrderId(item.id) && isOrderId(item.order_item_id) && !ids.has(item.order_item_id)
      && Number.isInteger(item.quantity) && item.quantity >= 1 && nullableText(item.reason))
    ids.add(item.order_item_id)
  }
  return value
}
export function validateReturnList(value: ReturnList, page: number): ReturnList {
  requireValid(value && Array.isArray(value.data) && Number.isInteger(value.total) && value.total >= 0
    && value.page === page && Number.isInteger(value.total_pages) && value.total_pages === Math.max(1, Math.ceil(value.total / 10))
    && value.data.length <= 10 && value.data.length <= value.total)
  value.data.forEach(validateReturnRow)
  requireValid(new Set(value.data.map((row) => row.id)).size === value.data.length)
  return value
}
const statuses: Record<string, { label: string; description: string }> = {
  requested: { label: 'Requested', description: 'Your request is awaiting review. Do not send items back until you receive instructions.' },
  approved: { label: 'Approved', description: 'Your return is approved. Follow the instructions you receive before sending items back.' },
  rejected: { label: 'Rejected', description: 'Your request was rejected. Review the notes or contact support if you need help.' },
  received: { label: 'Received', description: 'The returned items are marked received. This does not confirm a refund.' },
  refunded: { label: 'Refunded', description: 'The backend marks this return refunded. This screen does not provide an amount, transfer receipt or bank confirmation.' },
}
export const returnStatus = (status: string) => Object.hasOwn(statuses, status) ? statuses[status] : { label: 'Status unavailable', description: 'This status is not recognised by this version. Contact support for confirmation.' }
