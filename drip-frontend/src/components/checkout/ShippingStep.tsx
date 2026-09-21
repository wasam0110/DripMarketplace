import { useFormContext } from 'react-hook-form'
import { Input } from '@/components/ui/Input'
import type { CheckoutFormValues } from '@/lib/schemas/checkout'

const PROVINCES = ['Sindh', 'Punjab', 'KPK', 'Balochistan', 'Islamabad', 'Gilgit-Baltistan', 'AJK']

export function ShippingStep() {
  const { register, formState: { errors } } = useFormContext<CheckoutFormValues>()
  return (
    <div className="flex flex-col gap-4">
      <h3 className="font-bold text-sm tracking-wide">Shipping address</h3>
      <Input label="Street address" error={errors.street?.message} {...register('street')} placeholder="House 12, Street 4, DHA Phase 2" />
      <div className="grid grid-cols-2 gap-4">
        <Input label="City"     error={errors.city?.message}     {...register('city')}     placeholder="Karachi" />
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold tracking-widest text-muted uppercase">Province</label>
          <select {...register('province')}
            className="input-base text-sm">
            <option value="">Select province</option>
            {PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          {errors.province && <p className="text-xs text-danger">{errors.province.message}</p>}
        </div>
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-[10px] font-bold tracking-widest text-muted uppercase">Order notes <span className="normal-case font-normal">(optional)</span></label>
        <textarea {...register('notes')} rows={2}
          className="input-base resize-none" placeholder="Anything the courier should know?" />
      </div>
    </div>
  )
}
