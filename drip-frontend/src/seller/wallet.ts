import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'

export interface WalletSummary { available_balance: string; pending_balance: string; total_earned: string; total_commission: string; minimum_withdrawal_amount: string; maximum_withdrawal_amount: string }
export interface BankAccount { id: string; bank_name: string | null; account_title: string | null; account_number: string | null; is_default: boolean; created_at: string }
export interface BankDraft { bank_name: string; account_title: string; account_number: string; is_default: boolean }
export interface BankPayload { bank_name: string; account_title: string | null; account_number: string; is_default: boolean }
export interface WalletTransaction { id: string; type: string; amount: string; balance_after: string; reference: string | null; note: string | null; created_at: string }
export interface Payout { id: string; amount: string; payment_method: string; payment_detail: string; status: string; admin_note: string | null; requested_at: string; completed_at: string | null; transfer_reference: string | null }
export interface WalletPage<T> { data: T[]; total: number; page: number; total_pages: number; per_page?: number }
export interface Withdrawal { amount: string; bank_account_id: string; note?: string }
const money = (v: unknown, signed = false): v is string => typeof v === 'string' && (signed ? /^-?\d{1,10}(\.\d{1,2})?$/ : /^\d{1,10}(\.\d{1,2})?$/).test(v)
const text = (v: unknown): v is string => typeof v === 'string' && !!v.trim()
const nullableText = (v: unknown) => v === null || typeof v === 'string'
const date = (v: unknown) => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(v) && Number.isFinite(Date.parse(v))
const fail = () => { throw new Error('The wallet information could not be verified. Refresh to try again.') }
export const transactionTypes = ['credit_commission', 'debit_commission', 'credit_refund', 'debit_withdrawal', 'credit_adjustment', 'debit_adjustment']
export const payoutStatuses = ['requested', 'approved', 'processing', 'completed', 'rejected']
export function validateWallet(value: WalletSummary) {
  if (!value || !money(value.available_balance) || !money(value.pending_balance) || !money(value.total_earned, true) || !money(value.total_commission, true)
    || !money(value.minimum_withdrawal_amount) || !money(value.maximum_withdrawal_amount)
    || paisa(value.minimum_withdrawal_amount) < 50000n || paisa(value.minimum_withdrawal_amount) > paisa(value.maximum_withdrawal_amount)) return fail()
  return value
}
export function validateBank(value: BankAccount) {
  if (!value || typeof value.id !== 'string' || !isOrderId(value.id) || ![value.bank_name, value.account_title, value.account_number].every(nullableText)
    || typeof value.is_default !== 'boolean' || !date(value.created_at)) return fail()
  return value
}
export function validateBanks(value: BankAccount[]) {
  if (!Array.isArray(value)) return fail()
  const ids = new Set<string>()
  for (const row of value) { validateBank(row); if (ids.has(row.id)) return fail(); ids.add(row.id) }
  return value
}
export const usableBank = (value: BankAccount) => text(value.bank_name) && text(value.account_number)
export function bankPayload(value: BankDraft): BankPayload {
  const bank = value.bank_name.trim(), title = value.account_title.trim(), number = value.account_number.trim()
  if (!bank || bank.length > 100 || title.length > 200 || !number || number.length > 50 || /[\x00-\x1f\x7f]/.test(bank + title + number)) throw new Error('Enter a bank name (up to 100 characters), account number (up to 50) and optional title (up to 200).')
  return { bank_name: bank, account_title: title || null, account_number: number, is_default: value.is_default }
}
export function confirmBank(value: BankAccount, body: BankPayload) {
  validateBank(value)
  if (value.bank_name !== body.bank_name || value.account_title !== body.account_title || value.account_number !== body.account_number || value.is_default !== body.is_default) return fail()
  return value
}
export function withdrawalBody(amount: string, bankId: string, note: string, wallet: WalletSummary, accounts: BankAccount[]): Withdrawal {
  validateWallet(wallet)
  if (!money(amount)) throw new Error('Enter a PKR amount with up to two decimal places.')
  if (paisa(amount) < paisa(wallet.minimum_withdrawal_amount) || paisa(amount) > paisa(wallet.maximum_withdrawal_amount)) throw new Error('The amount is outside the current withdrawal limits.')
  if (paisa(amount) > paisa(wallet.available_balance)) throw new Error('The amount exceeds your available balance.')
  const account = accounts.find((row) => row.id === bankId)
  if (!account || !usableBank(account)) throw new Error('Select one of your bank payout accounts.')
  if (note.trim().length > 300) throw new Error('Use a note of 300 characters or fewer.')
  const units = paisa(amount)
  return { amount: `${units / 100n}.${String(units % 100n).padStart(2, '0')}`, bank_account_id: bankId, ...(note.trim() ? { note: note.trim() } : {}) }
}
export function validatePayout(value: Payout) {
  if (!value || typeof value.id !== 'string' || !isOrderId(value.id) || !money(value.amount) || !text(value.payment_method) || !text(value.payment_detail) || !text(value.status)
    || !nullableText(value.admin_note) || !nullableText(value.transfer_reference) || !date(value.requested_at) || !(value.completed_at === null || date(value.completed_at))) return fail()
  return value
}
export function confirmWithdrawal(value: Payout, body: Withdrawal, account: BankAccount) {
  validatePayout(value)
  if (body.bank_account_id !== account.id || paisa(value.amount) !== paisa(body.amount) || value.status !== 'requested' || value.payment_method !== 'bank_transfer'
    || value.payment_detail !== `${account.bank_name} — ${account.account_number}` || value.completed_at !== null || value.transfer_reference !== null) return fail()
  return value
}
export function validateWalletPage<T extends { id: string }>(value: WalletPage<T>, page: number, validate: (row: T) => T) {
  if (!value || !Array.isArray(value.data) || !Number.isSafeInteger(value.total) || value.total < 0 || value.page !== page
    || value.total_pages !== Math.max(1, Math.ceil(value.total / 25)) || value.data.length > 25 || value.data.length > value.total) return fail()
  const ids = new Set<string>()
  for (const row of value.data) { validate(row); if (ids.has(row.id)) return fail(); ids.add(row.id) }
  return value
}
export function validateTransaction(row: WalletTransaction) {
  if (!row || typeof row.id !== 'string' || !isOrderId(row.id) || !text(row.type) || !money(row.amount, true) || !money(row.balance_after, true)
    || !nullableText(row.reference) || !nullableText(row.note) || !date(row.created_at)) return fail()
  return row
}
export function payoutLabel(status: string) { switch (status) { case 'requested': return 'Requested'; case 'approved': return 'Approved'; case 'processing': return 'Processing'; case 'completed': return 'Transfer recorded'; case 'rejected': return 'Rejected'; default: return 'Status unavailable' } }
export const walletMarker = (owner: string) => `wearhowz:wallet-pending:${owner}`
export const maskAccount = (number: string | null) => number ? `•••• ${number.slice(-4)}` : 'Account number unavailable'
