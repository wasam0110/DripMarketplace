import { useSellerProfile } from '@/hooks/useSeller'
import { Skeleton } from '@/components/ui/Skeleton'

export default function SellerSettingsPage() {
  const { data: profile, isLoading } = useSellerProfile()
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Settings</h1>
      <div className="panel flex flex-col gap-4">
        <p className="text-xs font-bold tracking-widest text-muted uppercase">Brand details</p>
        {isLoading ? <Skeleton className="h-20 w-full" /> : profile ? (
          <div className="flex flex-col gap-2 text-sm">
            <p><span className="text-muted">Brand: </span>{profile.brand_name}</p>
            <p><span className="text-muted">Status: </span>{profile.status}</p>
            <p><span className="text-muted">WhatsApp: </span>{profile.whatsapp_number}</p>
            <p><span className="text-muted">Slots: </span>{profile.slot_count}</p>
          </div>
        ) : null}
      </div>
    </div>
  )
}
