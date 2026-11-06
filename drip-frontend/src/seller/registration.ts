import { paisa } from '../checkout/preview'
import { isOrderId } from '../orders/api'

export interface RegistrationPricing {
  registration_fee: string; base_slots: number; extra_slots: number; extra_slot_price: string
  extra_cost: string; total_cost: string; total_slots: number
}
export interface RegistrationResult { seller_id: string; amount_due: string; message: string }
export const registrationMarker = 'wearhowz:seller-registration-submitted:v1'
export function extraSlots(value: string): number | null {
  return /^\d{1,5}$/.test(value) && Number(value) <= 10000 ? Number(value) : null
}
function money(value: unknown): value is string {
  return typeof value === 'string' && /^\d{1,8}(\.\d{1,2})?$/.test(value)
}
export function validateRegistrationPricing(value: RegistrationPricing, requested: number): RegistrationPricing {
  if (!value || !Number.isSafeInteger(value.base_slots) || value.base_slots < 0
    || !Number.isSafeInteger(value.extra_slots) || value.extra_slots !== requested
    || requested < 0 || requested > 10000 || !Number.isSafeInteger(value.total_slots)
    || value.total_slots !== value.base_slots + requested
    || ![value.registration_fee, value.extra_slot_price, value.extra_cost, value.total_cost].every(money)
    || paisa(value.extra_slot_price) * BigInt(requested) !== paisa(value.extra_cost)
    || paisa(value.registration_fee) + paisa(value.extra_cost) !== paisa(value.total_cost)) {
    throw new Error('Registration pricing could not be verified. Refresh pricing before continuing.')
  }
  return value
}
export function samePricing(a: RegistrationPricing, b: RegistrationPricing) {
  return a.base_slots === b.base_slots && a.extra_slots === b.extra_slots && a.total_slots === b.total_slots
    && (['registration_fee', 'extra_slot_price', 'extra_cost', 'total_cost'] as const).every((key) => paisa(a[key]) === paisa(b[key]))
}
export function validateRegistrationResult(value: RegistrationResult): RegistrationResult {
  if (!value || typeof value.seller_id !== 'string' || !isOrderId(value.seller_id)
    || !money(value.amount_due) || typeof value.message !== 'string' || !value.message.trim()) {
    throw new Error('The application response could not be confirmed. Check your email or contact support before trying again.')
  }
  return value
}
export const registrationMoney = (value: string) => new Intl.NumberFormat('en-PK', {
  style: 'currency', currency: 'PKR', minimumFractionDigits: 2, maximumFractionDigits: 2,
}).format(Number(value))
