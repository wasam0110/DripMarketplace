import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { MessageCircle, Mail, ArrowUpRight } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { toast } from '@/components/ui/Toast'
import { whatsappLink } from '@/utils/whatsapp'

const schema = z.object({
  name:    z.string().min(2, 'Enter your name'),
  email:   z.string().email('Enter a valid email'),
  subject: z.string().min(3, 'Enter a subject'),
  message: z.string().min(20, 'Message must be at least 20 characters'),
})
type FormValues = z.infer<typeof schema>

const FAQS = [
  { q: 'How long does delivery take?',          a: 'Most orders are delivered within 3-5 business days across Pakistan. Karachi, Lahore, and Islamabad are usually faster.' },
  { q: 'Can I return an item?',                 a: "Returns are handled by each seller individually. Check the seller's return policy on the product page before purchasing." },
  { q: 'How do I track my order?',              a: 'Go to Account → Orders to see real-time status updates for all your orders.' },
  { q: 'Is cash on delivery available?',        a: 'Yes — COD is available on orders up to PKR 25,000. Our team will call to confirm before dispatching.' },
  { q: 'I want to sell on DRIP — how?',         a: 'Head to the Sell page and fill in your brand details. We review applications within 48 hours.' },
  { q: 'My payment failed — what do I do?',     a: 'Try again or switch to COD. If the amount was deducted but the order was not placed, contact us and we will resolve it within 24 hours.' },
]

export default function ContactPage() {
  const [sent, setSent] = useState(false)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(data: FormValues) {
    await new Promise(r => setTimeout(r, 800))
    setSent(true)
    toast.success("Message sent! We'll get back to you within 24 hours.")
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 flex flex-col gap-16">
      <div>
        <p className="text-[10px] font-mono font-bold tracking-widest text-muted mb-2">GET IN TOUCH</p>
        <h1 className="text-4xl font-bold">Contact us.</h1>
        <p className="text-muted text-sm mt-3 max-w-md">
          We're a small team — we read every message and reply within 24 hours on business days.
        </p>
      </div>

      <div className="grid sm:grid-cols-[1fr_360px] gap-12">
        <div className="flex flex-col gap-6">
          {sent ? (
            <div className="panel flex flex-col gap-4 items-start">
              <p className="text-accent text-3xl font-bold font-mono">✓</p>
              <h2 className="text-xl font-bold">Message received.</h2>
              <p className="text-muted text-sm">We'll reply to your email within 24 hours on business days.</p>
              <button onClick={() => setSent(false)} className="btn-outline text-xs">Send another</button>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <Input label="Your name" error={errors.name?.message}  {...register('name')}  placeholder="Ahmed Khan" />
                <Input label="Email"     error={errors.email?.message} {...register('email')} placeholder="ahmed@example.com" type="email" />
              </div>
              <Input label="Subject" error={errors.subject?.message} {...register('subject')} placeholder="Order issue / General question / Seller enquiry" />
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold tracking-widest text-muted uppercase">Message</label>
                <textarea {...register('message')} rows={6} className="input-base resize-none"
                  placeholder="Describe your issue or question in detail..." />
                {errors.message && <p className="text-xs text-danger">{errors.message.message}</p>}
              </div>
              <Button type="submit" loading={isSubmitting} className="self-start">
                Send message <ArrowUpRight size={15} />
              </Button>
            </form>
          )}
        </div>

        <div className="flex flex-col gap-6">
          <div className="panel flex flex-col gap-4">
            <p className="text-[10px] font-bold tracking-widest text-muted uppercase">Faster options</p>
            <a href={whatsappLink('923083062410', 'Hi DRIP team, I need help with...')}
              target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 border border-whatsapp/20 hover:border-whatsapp/50 transition-colors group">
              <MessageCircle size={18} className="text-whatsapp shrink-0" />
              <div>
                <p className="text-sm font-bold">WhatsApp</p>
                <p className="text-xs text-muted">Usually responds in minutes</p>
              </div>
              <ArrowUpRight size={14} className="ml-auto text-muted group-hover:text-white transition-colors" />
            </a>
            <a href="mailto:support@drip.pk"
              className="flex items-center gap-3 p-4 border border-border hover:border-muted transition-colors group">
              <Mail size={18} className="text-muted shrink-0" />
              <div>
                <p className="text-sm font-bold">Email</p>
                <p className="text-xs text-muted">support@drip.pk</p>
              </div>
              <ArrowUpRight size={14} className="ml-auto text-muted group-hover:text-white transition-colors" />
            </a>
          </div>

          <div className="panel flex flex-col gap-2">
            <p className="text-[10px] font-bold tracking-widest text-muted uppercase mb-1">Hours</p>
            <div className="flex justify-between text-xs"><span className="text-muted">Monday – Friday</span><span>10am – 7pm PKT</span></div>
            <div className="flex justify-between text-xs"><span className="text-muted">Saturday</span><span>11am – 4pm PKT</span></div>
            <div className="flex justify-between text-xs"><span className="text-muted">Sunday</span><span className="text-muted">Closed</span></div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-6">
        <div>
          <p className="text-[10px] font-mono font-bold tracking-widest text-muted mb-2">BEFORE YOU WRITE</p>
          <h2 className="text-2xl font-bold">Common questions.</h2>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          {FAQS.map(faq => (
            <div key={faq.q} className="panel flex flex-col gap-2">
              <p className="text-sm font-bold">{faq.q}</p>
              <p className="text-xs text-muted leading-relaxed">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}