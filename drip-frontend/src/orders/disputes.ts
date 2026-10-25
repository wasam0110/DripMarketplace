import { ApiError } from '../api/client'
import { isOrderId } from './api'

export interface DisputeMessage { id: string; sender_id: string; body: string; created_at: string }
export interface DisputeDetail {
  id: string; return_id: string; seller_id: string; status: string; resolution_note: string | null
  created_at: string; resolved_at: string | null; messages: DisputeMessage[]
}
const validDate = (value: unknown) => typeof value === 'string' && Number.isFinite(Date.parse(value))
function valid(condition: unknown): asserts condition {
  if (!condition) throw new Error('Dispute details could not be confirmed. Refresh or contact support before repeating a change.')
}
export function validateMessage(value: DisputeMessage): DisputeMessage {
  valid(value && isOrderId(value.id) && isOrderId(value.sender_id) && typeof value.body === 'string' && value.body.length > 0 && validDate(value.created_at))
  return value
}
export function validateDispute(value: DisputeDetail, returnId: string): DisputeDetail {
  valid(value && isOrderId(value.id) && value.return_id === returnId && isOrderId(value.seller_id)
    && typeof value.status === 'string' && value.status.length > 0 && validDate(value.created_at)
    && (value.resolved_at === null || validDate(value.resolved_at))
    && (value.resolution_note === null || typeof value.resolution_note === 'string') && Array.isArray(value.messages))
  value.messages.forEach(validateMessage)
  valid(new Set(value.messages.map((message) => message.id)).size === value.messages.length)
  return value
}
export function disputeText(value: string, opening: boolean): string {
  const text = value.trim(), min = opening ? 10 : 1
  if (text.length < min || text.length > 2000) throw new Error(`Enter ${min}–2,000 characters${opening ? ' explaining your dispute' : ' for your message'}.`)
  return text
}
// A generic 404 may mean revoked ownership; only this backend sentinel means no dispute.
export const missingDispute = (error: unknown) => error instanceof ApiError && error.status === 404 && error.code === 'NOT_FOUND' && error.message === 'No dispute found for this return not found.'
export const canMessage = (status: string) => status === 'open' || status === 'under_review'
const labels: Record<string, string> = { open: 'Open', under_review: 'Under review', resolved_customer: 'Resolved in customer’s favour', resolved_seller: 'Resolved in seller’s favour', closed: 'Closed' }
export const disputeStatus = (status: string) => Object.hasOwn(labels, status) ? labels[status] : 'Status unavailable'
