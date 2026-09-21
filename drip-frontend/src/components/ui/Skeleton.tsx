interface SkeletonProps { className?: string; count?: number }

export function Skeleton({ className = 'h-4 w-full' }: SkeletonProps) {
  return <div className={`bg-card animate-pulse ${className}`} />
}

export function ProductCardSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <Skeleton className="aspect-[3/4] w-full bg-card" />
      <Skeleton className="h-3 w-1/3" />
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-4 w-1/4" />
    </div>
  )
}

export function TableRowSkeleton({ cols = 4 }: { cols?: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3"><Skeleton className="h-3 w-full" /></td>
      ))}
    </tr>
  )
}
