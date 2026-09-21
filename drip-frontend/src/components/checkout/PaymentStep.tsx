import { useFormContext } from 'react-hook-form'
import type { CheckoutFormValues } from '@/lib/schemas/checkout'

const METHODS = [
  { value: 'payfast', label: 'PayFast',         desc: 'Pay securely via PayFast — debit card, credit card, or bank transfer' },
  { value: 'cod',     label: 'Cash on delivery', desc: 'Pay in cash when your order arrives (requires phone verification)' },
]

export function PaymentStep() {
  const { register, watch } = useFormContext<CheckoutFormValues>()
  const selected = watch('method')

  return (
    <div className="flex flex-col gap-3">
      <h3 className="font-bold text-sm tracking-wide">Payment method</h3>
      {METHODS.map(m => (
        <label key={m.value} className={`flex items-start gap-3 p-4 border cursor-pointer transition-colors
          ${selected === m.value ? 'border-accent bg-accent/5' : 'border-border hover:border-muted'}`}>
          <input type="radio" value={m.value} {...register('method')} className="mt-0.5 accent-[#DFFF00]" />
          <div>
            <p className="text-sm font-bold">{m.label}</p>
            <p className="text-xs text-muted">{m.desc}</p>
          </div>
        </label>
      ))}
    </div>
  )
}
