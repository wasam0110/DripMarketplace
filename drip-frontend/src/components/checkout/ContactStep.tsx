import { useFormContext } from 'react-hook-form'
import { Input } from '@/components/ui/Input'
import type { CheckoutFormValues } from '@/lib/schemas/checkout'

export function ContactStep() {
  const { register, formState: { errors } } = useFormContext<CheckoutFormValues>()
  return (
    <div className="flex flex-col gap-4">
      <h3 className="font-bold text-sm tracking-wide">Contact details</h3>
      <Input label="Full name"    error={errors.recipient_name?.message} {...register('recipient_name')} placeholder="Ahmed Khan" />
      <Input label="Phone"        error={errors.phone?.message}          {...register('phone')}          placeholder="03001234567" />
    </div>
  )
}
