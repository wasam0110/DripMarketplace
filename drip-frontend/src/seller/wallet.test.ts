import { expect, it } from 'vitest'
import { bankPayload, confirmBank, confirmWithdrawal, validateBanks, validateWallet, withdrawalBody, type BankAccount, type Payout } from './wallet'
const wallet = { available_balance: '1000.25', pending_balance: '500.00', total_earned: '2000.00', total_commission: '100.00', minimum_withdrawal_amount: '750', maximum_withdrawal_amount: '1250' }
const account: BankAccount = { id: '11111111-1111-4111-8111-111111111111', bank_name: 'Test Bank', account_title: 'Test Brand', account_number: 'PK00TEST1234', is_default: false, created_at: '2026-10-28T10:00:00Z' }
const payout: Payout = { id: '22222222-2222-4222-8222-222222222222', amount: '750.25', payment_method: 'bank_transfer', payment_detail: 'Test Bank — PK00TEST1234', status: 'requested', admin_note: null, requested_at: '2026-10-28T10:00:00Z', completed_at: null, transfer_reference: null }
it('uses configured limits and exact cents for withdrawals', () => {
  expect(withdrawalBody('00750.25', account.id, '  Payout please  ', wallet, [account])).toEqual({ amount: '750.25', bank_account_id: account.id, note: 'Payout please' })
  expect(() => withdrawalBody('749.99', account.id, '', wallet, [account])).toThrow('limits')
  expect(() => withdrawalBody('1000.26', account.id, '', wallet, [account])).toThrow('available')
})
it.each(['NaN', 'Infinity', '1e3', '750.001', '-750', '', '99999999999'])('rejects malformed amount %s', (amount) => {
  expect(() => withdrawalBody(amount, account.id, '', wallet, [account])).toThrow()
})
it('requires a bank account in the current owning account list', () => {
  expect(() => withdrawalBody('750', payout.id, '', wallet, [account])).toThrow()
  expect(() => withdrawalBody('750', account.id, '', wallet, [{ ...account, bank_name: null }])).toThrow()
})
it('requires configured limits before accepting withdrawal input', () => {
  expect(() => validateWallet({ ...wallet, maximum_withdrawal_amount: '500' })).toThrow()
  expect(() => validateWallet({ ...wallet, minimum_withdrawal_amount: undefined! })).toThrow()
})
it('validates bank creation and exact returned account fields', () => {
  const body = bankPayload({ bank_name: ' Test Bank ', account_title: ' Test Brand ', account_number: ' PK00TEST1234 ', is_default: false })
  expect(confirmBank(account, body)).toEqual(account)
  expect(() => confirmBank({ ...account, account_number: 'WRONG' }, body)).toThrow()
  expect(() => bankPayload({ bank_name: ' ', account_title: '', account_number: '123', is_default: false })).toThrow()
  expect(() => validateBanks([account, account])).toThrow()
})
it('confirms requested amount and destination rather than implying a transfer', () => {
  const body = withdrawalBody('750.25', account.id, '', wallet, [account])
  expect(confirmWithdrawal(payout, body, account)).toEqual(payout)
  expect(() => confirmWithdrawal({ ...payout, amount: '850.25' }, body, account)).toThrow()
  expect(() => confirmWithdrawal({ ...payout, payment_detail: 'Other Bank — 9999' }, body, account)).toThrow()
  expect(() => confirmWithdrawal({ ...payout, status: 'completed' }, body, account)).toThrow()
  expect(() => confirmWithdrawal(payout, { ...body, bank_account_id: payout.id }, account)).toThrow()
})
