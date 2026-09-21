import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { pkr } from '@/utils/currency'
import type { WalletBalance } from '@/types/seller'

export function WalletCard({ wallet }: { wallet: WalletBalance }) {
  return (
    <div className="panel flex flex-col gap-4">
      <p className="text-[10px] font-bold tracking-widest text-muted uppercase">Wallet</p>
      <div>
        <p className="text-3xl font-bold">{pkr(wallet.available_balance)}</p>
        <p className="text-xs text-muted mt-1">available to withdraw</p>
      </div>
      {wallet.pending_balance > 0 && (
        <p className="text-xs text-muted">
          <span className="text-warning font-bold">{pkr(wallet.pending_balance)}</span> pending settlement
        </p>
      )}
      <Link to="/dashboard/wallet" className="btn-outline text-xs self-start">
        Manage wallet <ArrowUpRight size={13} />
      </Link>
    </div>
  )
}
