import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FormProvider, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { checkoutSchema, type CheckoutFormValues } from '@/lib/schemas/checkout'
import { ContactStep } from '@/components/checkout/ContactStep'
import { ShippingStep } from '@/components/checkout/ShippingStep'
import { PaymentStep } from '@/components/checkout/PaymentStep'
import { Button } from '@/components/ui/Button'
import { useCartStore } from '@/store/cartStore'
import { useAuthStore } from '@/store/authStore'
import { usePlaceOrder } from '@/hooks/useOrders'
import { toast } from '@/components/ui/Toast'
import { pkr } from '@/utils/currency'
import { getErrorMessage } from '@/utils/errorHandler'

const STEPS = ['Contact', 'Shipping', 'Payment']

export default function CheckoutPage() {
  const [step, setStep] = useState(0)
  const items  = useCartStore(s => s.items)
  const total  = useCartStore(s => s.total())
  const user   = useAuthStore(s => s.user)
  const place  = usePlaceOrder()
  const navigate = useNavigate()

  const methods = useForm<CheckoutFormValues>({
    resolver: zodResolver(checkoutSchema),
    defaultValues: { method: 'cod' },
  })

  async function onSubmit(data: CheckoutFormValues) {
    try {
      const result = await place.mutateAsync({
        items: items.map(i => ({ variant_id: i.variant_id, quantity: i.quantity })),
        shipping_address: { recipient_name: data.recipient_name, phone: data.phone, street: data.street, city: data.city, province: data.province },
        payment_method: data.method,
        notes: data.notes,
      })
      navigate(`/order/success/${result.order_id}`)
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  if (!user) return (
    <div className="max-w-sm mx-auto px-4 py-20 text-center flex flex-col gap-4">
      <p className="text-muted text-sm">Sign in to complete your order.</p>
      <Button onClick={() => navigate('/login', { state: { from: '/checkout' } })}>Sign in</Button>
    </div>
  )

  if (items.length === 0) return (
    <div className="max-w-sm mx-auto px-4 py-20 text-center flex flex-col gap-4">
      <p className="text-muted text-sm">Your bag is empty.</p>
      <Button variant="outline" onClick={() => navigate('/shop')}>Shop now</Button>
    </div>
  )

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10 grid sm:grid-cols-[1fr_320px] gap-10">
      {/* Form */}
      <FormProvider {...methods}>
        <form onSubmit={methods.handleSubmit(onSubmit)} className="flex flex-col gap-8">
          {/* Step indicators */}
          <div className="flex gap-0">
            {STEPS.map((s, i) => (
              <button key={s} type="button" onClick={() => i < step && setStep(i)}
                className={`flex-1 py-2 text-[10px] font-bold tracking-widest border-b-2 transition-colors
                  ${i === step ? 'border-accent text-accent' : i < step ? 'border-border text-muted cursor-pointer hover:text-white' : 'border-border text-border cursor-default'}`}>
                {s}
              </button>
            ))}
          </div>

          {step === 0 && <ContactStep />}
          {step === 1 && <ShippingStep />}
          {step === 2 && <PaymentStep />}

          <div className="flex gap-3">
            {step > 0 && <Button type="button" variant="outline" onClick={() => setStep(s => s - 1)}>Back</Button>}
            {step < 2
              ? <Button type="button" onClick={async () => {
                  const fields: (keyof CheckoutFormValues)[][] = [['recipient_name', 'phone'], ['street', 'city', 'province'], ['method']]
                  const ok = await methods.trigger(fields[step] as any)
                  if (ok) setStep(s => s + 1)
                }} className="flex-1 justify-center">Continue</Button>
              : <Button type="submit" loading={place.isPending} className="flex-1 justify-center">Place order</Button>
            }
          </div>
        </form>
      </FormProvider>

      {/* Order summary */}
      <aside className="flex flex-col gap-4">
        <h2 className="font-bold text-sm tracking-wide border-b border-border pb-4">Order summary</h2>
        <div className="flex flex-col divide-y divide-border">
          {items.map(i => (
            <div key={i.id} className="py-3 flex gap-3">
              <div className="w-12 h-14 bg-card shrink-0 overflow-hidden">
                {i.image_url && <img src={i.image_url} alt={i.product_name} className="w-full h-full object-cover" />}
              </div>
              <div className="flex-1 flex flex-col gap-0.5">
                <p className="text-xs font-medium line-clamp-2">{i.product_name}</p>
                <p className="text-[10px] text-muted">{i.colour} / {i.size_value} × {i.quantity}</p>
                <p className="text-xs font-bold">{pkr(i.unit_price * i.quantity)}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="border-t border-border pt-4 flex flex-col gap-2">
          <div className="flex justify-between text-xs text-muted"><span>Subtotal</span><span>{pkr(total)}</span></div>
          <div className="flex justify-between text-xs text-muted"><span>Shipping</span><span>Calculated after order</span></div>
          <div className="flex justify-between font-bold mt-1"><span>Total</span><span>{pkr(total)}</span></div>
        </div>
      </aside>
    </div>
  )
}
