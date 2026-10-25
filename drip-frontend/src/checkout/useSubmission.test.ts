import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { checkoutRequest, rememberKey, storageKey, type OrderResult } from './submission'
import { useSubmission } from './useSubmission'

vi.mock('./submission', async (original) => ({ ...await original<typeof import('./submission')>(), checkoutRequest: vi.fn() }))
const key = '11111111-1111-4111-8111-111111111111'
const order: OrderResult = { order_id: key, order_number: 'WHZ-1', total: '100', status: 'pending_cod_verification', payment_method: 'cod', guest_token: null, whatsapp_url: null }
const body = { quote_token: 'accepted', shipping_address: { street: 'Private street' } }
beforeEach(() => { sessionStorage.clear(); vi.resetAllMocks() })
it('coalesces double clicks and stores only the key before sending', async () => {
  vi.mocked(checkoutRequest).mockResolvedValue(order)
  const success = vi.fn()
  const { result } = renderHook(() => useSubmission('guest', success, vi.fn()))
  act(() => { result.current.submit(body); result.current.submit(body) })
  await waitFor(() => expect(result.current.result).toEqual(order))
  expect(checkoutRequest).toHaveBeenCalledOnce()
  expect(sessionStorage.getItem(storageKey('guest'))).toMatch(/^[\da-f-]{36}$/)
  expect(JSON.stringify({ ...sessionStorage })).not.toContain('Private')
  expect(success).toHaveBeenCalledOnce()
})
it('retries an uncertain response with the identical payload and key', async () => {
  vi.mocked(checkoutRequest).mockRejectedValueOnce(new ApiError('Lost', 0)).mockResolvedValueOnce(order)
  const { result } = renderHook(() => useSubmission('guest', vi.fn(), vi.fn()))
  act(() => result.current.submit(body))
  await waitFor(() => expect(result.current.error).toBeTruthy())
  expect(result.current.blocked).toBe(true)
  act(() => result.current.retry())
  await waitFor(() => expect(result.current.result).toEqual(order))
  expect(vi.mocked(checkoutRequest).mock.calls[0][1]).toEqual(vi.mocked(checkoutRequest).mock.calls[1][1])
})
it('requires recovery on reload and never clears an unknown guest selection', async () => {
  rememberKey('guest', key)
  vi.mocked(checkoutRequest).mockResolvedValue(order)
  const success = vi.fn()
  const { result } = renderHook(() => useSubmission('guest', success, vi.fn()))
  expect(result.current.blocked).toBe(true)
  expect(result.current.canRetry).toBe(false)
  act(() => result.current.recover())
  await waitFor(() => expect(result.current.result).toEqual(order))
  expect(success).not.toHaveBeenCalled()
})
it('keeps the original key after not-found recovery to protect against delayed requests', async () => {
  rememberKey('guest', key)
  vi.mocked(checkoutRequest).mockRejectedValueOnce(new ApiError('Not found', 404)).mockResolvedValueOnce(order)
  const { result } = renderHook(() => useSubmission('guest', vi.fn(), vi.fn()))
  act(() => result.current.recover())
  await waitFor(() => expect(result.current.blocked).toBe(false))
  act(() => result.current.submit(body))
  await waitFor(() => expect(result.current.result).toEqual(order))
  expect(vi.mocked(checkoutRequest).mock.calls[1][1]).toMatchObject({ checkout_key: key })
})
it('requires another review after a rejected quote without automatically resubmitting', async () => {
  vi.mocked(checkoutRequest).mockRejectedValue(new ApiError('Changed', 409, 'CHECKOUT_QUOTE_CHANGED'))
  const review = vi.fn()
  const { result } = renderHook(() => useSubmission('guest', vi.fn(), review))
  act(() => result.current.submit(body))
  await waitFor(() => expect(review).toHaveBeenCalledOnce())
  expect(result.current.blocked).toBe(false)
  expect(result.current.canRetry).toBe(false)
  expect(checkoutRequest).toHaveBeenCalledOnce()
})
it('fails closed when tab storage cannot persist the key', () => {
  const { result } = renderHook(() => useSubmission('guest', vi.fn(), vi.fn()))
  const storage = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Blocked') })
  act(() => result.current.submit(body))
  expect(result.current.blocked).toBe(true)
  expect(checkoutRequest).not.toHaveBeenCalled()
  storage.mockRestore()
})
it('does not clear a new bag when recovering a key used for different details', async () => {
  vi.mocked(checkoutRequest).mockRejectedValueOnce(new ApiError('Reused', 409, 'CHECKOUT_KEY_REUSED')).mockResolvedValueOnce(order)
  const success = vi.fn()
  const { result } = renderHook(() => useSubmission('guest', success, vi.fn()))
  act(() => result.current.submit(body))
  await waitFor(() => expect(result.current.error).toBeTruthy())
  expect(result.current.canRetry).toBe(false)
  act(() => result.current.recover())
  await waitFor(() => expect(result.current.result).toEqual(order))
  expect(success).not.toHaveBeenCalled()
})
