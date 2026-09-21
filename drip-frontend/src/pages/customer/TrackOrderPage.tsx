import { useNavigate, Link } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from '@/store/authStore'
import { ArrowUpRight, PackageSearch } from 'lucide-react'

export default function TrackOrderPage() {
  const user     = useAuthStore(s => s.user)
  const navigate = useNavigate()

  useEffect(() => {
    if (user) navigate('/account/orders', { replace: true })
  }, [user, navigate])

  if (user) return null

  return (
    <div className="max-w-lg mx-auto px-4 sm:px-6 py-24 flex flex-col items-center gap-8 text-center">
      <PackageSearch size={48} className="text-border" />
      <div>
        <h1 className="text-2xl font-bold">Track your order.</h1>
        <p className="text-muted text-sm mt-2">Sign in to see real-time updates on all your DRIP orders.</p>
      </div>
      <div className="flex gap-3">
        <Link to="/login" className="btn-primary">Sign in <ArrowUpRight size={15} /></Link>
        <Link to="/register" className="btn-outline">Create account</Link>
      </div>
      <p className="text-xs text-muted">
        Need help? <Link to="/contact" className="text-white hover:text-accent transition-colors">Contact us</Link>
      </p>
    </div>
  )
}