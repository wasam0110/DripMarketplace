import type { AdminReturn } from '../../src/admin/returns'
import type { DisputeDetail } from '../../src/orders/disputes'
export const rid = '11111111-1111-4111-8111-111111111111', did = '22222222-2222-4222-8222-222222222222', owner = '33333333-3333-4333-8333-333333333333', other = '44444444-4444-4444-8444-444444444444'
export const when = '2026-11-05T10:00:00Z'
export function returned(status = 'requested'): AdminReturn {
  return { id: rid, order_id: other, seller_order_id: other, status, reason: 'The sleeve arrived damaged.', item_count: 1, requested_at: when, resolved_at: null, notes: null,
    items: [{ id: other, order_item_id: other, product_id: other, variant_id: other, product_name: 'Linen overshirt', variant_label: 'Olive / M', unit_price: '1200.00', purchased_quantity: 2, requested_quantity: 1, line_subtotal: '1200.00', reason: 'Damaged sleeve' }], estimated_refund_amount: '1080.00', available_actions: status === 'requested' ? ['approve', 'reject'] : status === 'approved' ? ['mark_received'] : status === 'received' ? ['request_refund'] : [],
    customer: { user_id: other, is_guest: false, first_name: 'Ayesha', last_name: 'Khan', email: 'customer@example.test', phone: '03001234567' }, seller: { seller_id: other, brand_name: 'Independent Label' },
    order: { order_id: other, order_number: 'WHZ-RET-001', status: 'delivered', payment_method: 'cod', subtotal: '2400.00', discount_amount: '240.00', shipping_fee: '200.00', total: '2360.00', payment_id: other, payment_status: 'completed', payment_currency: 'PKR' }, refund: null, dispute: null }
}
export function disputed(): DisputeDetail { return { id: did, return_id: rid, seller_id: other, status: 'open', resolution_note: null, created_at: when, resolved_at: null, messages: [{ id: other, sender_id: other, body: 'Please review the damaged sleeve.', created_at: when }] } }
