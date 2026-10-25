import { beforeEach, expect, it, vi } from 'vitest'
import { ApiError, refreshSession, request } from '../api/client'
import { checkoutRequest, rejectedBeforeCreation, rememberKey, safeWhatsapp, savedKey, storageKey, validateOrder, type OrderResult } from './submission'

vi.mock('../api/client', async (original) => ({ ...await original<typeof import('../api/client')>(), request: vi.fn(), refreshSession: vi.fn() }))
const key = '11111111-1111-4111-8111-111111111111'
const order: OrderResult = { order_id: key, order_number: 'WHZ-1', total: '100.01', status: 'pending_cod_verification', payment_method: 'cod', guest_token: 'private', whatsapp_url: null }
beforeEach(() => { sessionStorage.clear(); vi.clearAllMocks(); vi.mocked(request).mockResolvedValue(order) })
it('stores only a scoped key, not order/contact data', () => {
  rememberKey('guest', key)
  expect(savedKey('guest')).toBe(key)
  expect(savedKey('account')).toBeNull()
  expect(sessionStorage.getItem(storageKey('guest'))).toBe(key)
  expect(() => rememberKey('guest', 'invalid')).toThrow()
})
it('rejects malformed responses instead of claiming success', () => {
  expect(validateOrder(order)).toBe(order)
  expect(() => validateOrder({ ...order, total: 'NaN' })).toThrow()
  expect(() => validateOrder({ ...order, order_id: '' })).toThrow()
  expect(() => validateOrder({ ...order, payment_method: 'payfast' })).toThrow()
})
it('accepts a pending PayFast order for explicit later handoff', () => {
  const result = { ...order, status: 'pending_payment', payment_method: 'payfast', whatsapp_url: null }
  expect(validateOrder(result)).toBe(result)
})
it.each(['javascript:alert(1)', 'https://wa.me.evil.test/123', 'http://wa.me/123', 'https://name:secret@wa.me/123'])('rejects unsafe verification URL %s', (url) => {
  expect(safeWhatsapp(url)).toBeUndefined()
})
it('accepts only trusted HTTPS WhatsApp verification links', () => {
  expect(safeWhatsapp('https://wa.me/923001234567?text=WHZ-1')).toContain('https://wa.me/')
})
it('does not classify uncertain outcomes as rejected orders', () => {
  expect(rejectedBeforeCreation(new ApiError('Changed', 409, 'CHECKOUT_QUOTE_CHANGED'))).toBe(true)
  for (const status of [0, 401, 409, 429, 500, 502]) expect(rejectedBeforeCreation(new ApiError('Unknown', status))).toBe(false)
})
it('sends recovery keys in a JSON body, never a URL', async () => {
  await checkoutRequest('guest', key)
  expect(request).toHaveBeenCalledWith('/orders/guest/recover', expect.objectContaining({ body: JSON.stringify({ checkout_key: key }), authenticated: false }))
})
it('checks account ownership after refreshing before a write', async () => {
  await expect(checkoutRequest('account', key, () => false)).rejects.toThrow('session changed')
  expect(refreshSession).toHaveBeenCalledOnce()
  expect(request).not.toHaveBeenCalled()
})
it('rejects a response for a different payment method', async () => {
  await expect(checkoutRequest('guest', { checkout_key: key, quote_token: 'signed', payment_method: 'payfast' })).rejects.toThrow('payment method differs')
})
