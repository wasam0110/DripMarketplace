import { useSellerWallet } from '@/hooks/useSeller'
import { WalletCard } from '@/components/seller/WalletCard'
import { Skeleton } from '@/components/ui/Skeleton'

export default function SellerWalletPage() {
  const { data: wallet, isLoading } = useSellerWallet()
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Wallet</h1>
      {isLoading ? <Skeleton className="h-40 w-full" /> : wallet ? <WalletCard wallet={wallet} /> : null}
      <div className="panel">
        <p className="text-xs font-bold tracking-widest text-muted uppercase mb-4">Transaction history</p>
        <p className="text-muted text-sm">No transactions yet.</p>
      </div>
    </div>
  )
}
