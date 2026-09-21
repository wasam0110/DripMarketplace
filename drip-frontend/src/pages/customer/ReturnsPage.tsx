import { Link } from 'react-router-dom'
import { ArrowUpRight, AlertCircle, CheckCircle2, XCircle } from 'lucide-react'

const STEPS = [
  { step: '01', title: 'Check eligibility',  desc: 'Returns are accepted within 7 days of delivery on unworn, unwashed items with original tags. Sale items are final.' },
  { step: '02', title: 'Contact the seller', desc: 'Go to Account → Orders → your order and tap "Request return". The seller will respond within 48 hours.' },
  { step: '03', title: 'Ship it back',       desc: 'Pack the item securely and ship to the address provided by the seller. Keep your tracking number.' },
  { step: '04', title: 'Get refunded',       desc: 'Once the seller confirms receipt, your refund is processed within 3-5 business days to your original payment method.' },
]
const ELIGIBLE = [
  'Item received damaged or defective',
  'Wrong item or size sent',
  'Item significantly different from listing',
  'Unworn and unwashed with original tags attached',
]
const NOT_ELIGIBLE = [
  'Worn, washed, or altered items',
  'Items without original tags',
  'Sale or discounted items (marked as final sale)',
  'Requests made after 7 days of delivery',
  'Custom or made-to-order pieces',
]

export default function ReturnsPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-16 flex flex-col gap-16">
      <div>
        <p className="text-[10px] font-mono font-bold tracking-widest text-muted mb-2">RETURNS & REFUNDS</p>
        <h1 className="text-4xl font-bold">Return policy.</h1>
        <p className="text-muted text-sm mt-3 max-w-lg">
          Each seller on DRIP sets their own return policy. The details below are our platform-wide minimums —
          sellers may offer more generous terms which you'll find on their product pages.
        </p>
      </div>

      <div className="flex flex-col gap-6">
        <h2 className="text-xl font-bold">How returns work.</h2>
        <div className="grid sm:grid-cols-2 gap-4">
          {STEPS.map(s => (
            <div key={s.step} className="panel flex flex-col gap-3">
              <span className="font-mono text-accent font-bold text-sm">{s.step}</span>
              <p className="font-bold text-sm">{s.title}</p>
              <p className="text-xs text-muted leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-8">
        <div className="flex flex-col gap-4">
          <h3 className="font-bold flex items-center gap-2"><CheckCircle2 size={16} className="text-success" /> Eligible for return</h3>
          <ul className="flex flex-col gap-2">
            {ELIGIBLE.map(e => <li key={e} className="flex items-start gap-2 text-xs text-muted"><span className="text-success mt-0.5 shrink-0">✓</span>{e}</li>)}
          </ul>
        </div>
        <div className="flex flex-col gap-4">
          <h3 className="font-bold flex items-center gap-2"><XCircle size={16} className="text-danger" /> Not eligible</h3>
          <ul className="flex flex-col gap-2">
            {NOT_ELIGIBLE.map(e => <li key={e} className="flex items-start gap-2 text-xs text-muted"><span className="text-danger mt-0.5 shrink-0">✗</span>{e}</li>)}
          </ul>
        </div>
      </div>

      <div className="panel border-warning/30 bg-warning/5 flex gap-3">
        <AlertCircle size={16} className="text-warning shrink-0 mt-0.5" />
        <div className="flex flex-col gap-1">
          <p className="text-sm font-bold text-warning">COD orders</p>
          <p className="text-xs text-muted leading-relaxed">
            Cash on delivery orders that are refused at the door or returned without prior approval may result in
            your account being restricted from COD on future orders.
          </p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <Link to="/account/orders" className="btn-primary self-start">View my orders <ArrowUpRight size={15} /></Link>
        <Link to="/contact" className="btn-outline self-start">Contact support</Link>
      </div>
    </div>
  )
}