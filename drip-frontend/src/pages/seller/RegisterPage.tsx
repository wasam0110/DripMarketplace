import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowUpRight } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { sellerApi } from '@/api/seller.api'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { toast } from '@/components/ui/Toast'
import { getErrorMessage } from '@/utils/errorHandler'

const schema = z.object({
  email:           z.string().email(),
  password:        z.string().min(8),
  first_name:      z.string().min(2),
  brand_name:      z.string().min(2).max(100),
  description:     z.string().min(20).max(2000),
  whatsapp_number: z.string().regex(/^(\+92|0)?3[0-9]{9}$/, 'Enter a valid Pakistani number'),
  return_policy:   z.string().min(10).max(500),
})
type FormValues = z.infer<typeof schema>

function SellerRegisterPageForm() {
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: sellerApi.register,
    onSuccess: () => { toast.success('Application submitted! We review within 48h.'); navigate('/login') },
    onError: err => toast.error(getErrorMessage(err)),
  })
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({ resolver: zodResolver(schema) })

  return (
    <div className="max-w-xl mx-auto px-4 sm:px-6 py-16 flex flex-col gap-10">
      <div>
        <Link to="/" className="font-mono font-bold text-2xl">DRIP<span className="text-accent">.</span></Link>
        <h1 className="text-3xl font-bold mt-8">Start selling.</h1>
        <p className="text-muted text-sm mt-2">50 product slots. 85% of every sale. No hidden fees.</p>
      </div>
      <form onSubmit={handleSubmit(d => mutation.mutate(d))} className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-4">
          <Input label="First name" error={errors.first_name?.message}  {...register('first_name')} />
          <Input label="Brand name" error={errors.brand_name?.message}  {...register('brand_name')} placeholder="VOID FORM" />
        </div>
        <Input label="Email"    type="email"    error={errors.email?.message}    {...register('email')} />
        <Input label="Password" type="password" error={errors.password?.message} {...register('password')} />
        <Input label="WhatsApp" error={errors.whatsapp_number?.message} {...register('whatsapp_number')} placeholder="03001234567" />
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold tracking-widest text-muted uppercase">Brand description</label>
          <textarea {...register('description')} rows={3} className="input-base resize-none" placeholder="What your brand is about..." />
          {errors.description && <p className="text-xs text-danger">{errors.description.message}</p>}
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold tracking-widest text-muted uppercase">Return policy</label>
          <textarea {...register('return_policy')} rows={2} className="input-base resize-none" placeholder="e.g. 7-day returns on unworn items" />
          {errors.return_policy && <p className="text-xs text-danger">{errors.return_policy.message}</p>}
        </div>
        {mutation.error && <p className="text-xs text-danger">{getErrorMessage(mutation.error)}</p>}
        <Button type="submit" loading={mutation.isPending} className="justify-center mt-2">
          Apply to sell <ArrowUpRight size={15} />
        </Button>
      </form>
    </div>
  )
}

function CommissionRates() {
  const tiers = [
    { label: 'Registration fee',  value: 'PKR 5,000 one-time' },
    { label: 'Base slots',        value: '50 products included' },
    { label: 'Extra slots',       value: 'PKR 50 per additional slot' },
    { label: 'Commission rate',   value: '15% per sale' },
    { label: 'Seller keeps',      value: '85% of every sale' },
    { label: 'Payout schedule',   value: 'Weekly (every Monday)' },
    { label: 'Minimum payout',    value: 'PKR 500' },
    { label: 'Payment methods',   value: 'Bank transfer' },
  ]
  return (
    <section id="rates" className="max-w-2xl mx-auto px-4 sm:px-6 py-16 flex flex-col gap-8">
      <div>
        <p className="text-[10px] font-mono font-bold tracking-widest text-muted mb-2">TRANSPARENT PRICING</p>
        <h2 className="text-3xl font-bold">Commission rates.</h2>
        <p className="text-muted text-sm mt-2">No hidden fees. No monthly subscriptions. You only pay when you sell.</p>
      </div>
      <div className="panel flex flex-col divide-y divide-border">
        {tiers.map(t => (
          <div key={t.label} className="flex justify-between py-3 text-sm">
            <span className="text-muted">{t.label}</span>
            <span className="font-bold">{t.value}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function SellerRegisterPage() {
  return (
    <>
      <SellerRegisterPageForm />
      <CommissionRates />
    </>
  )
}