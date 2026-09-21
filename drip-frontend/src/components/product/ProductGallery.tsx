import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { ProductImage } from '@/types/product'

interface Props { images: ProductImage[]; name: string }

export function ProductGallery({ images, name }: Props) {
  const [active, setActive] = useState(0)
  if (!images.length) return <div className="aspect-square bg-card flex items-center justify-center text-muted text-xs font-mono">NO IMAGE</div>

  return (
    <div className="flex flex-col gap-3">
      {/* Main image */}
      <div className="relative aspect-square sm:aspect-[3/4] bg-card overflow-hidden">
        <img src={images[active].url} alt={`${name} ${active + 1}`} className="w-full h-full object-cover" />
        {images.length > 1 && (
          <>
            <button onClick={() => setActive(i => Math.max(0, i - 1))}
              className="absolute left-3 top-1/2 -translate-y-1/2 w-8 h-8 bg-bg/80 flex items-center justify-center hover:bg-bg">
              <ChevronLeft size={16} />
            </button>
            <button onClick={() => setActive(i => Math.min(images.length - 1, i + 1))}
              className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 bg-bg/80 flex items-center justify-center hover:bg-bg">
              <ChevronRight size={16} />
            </button>
          </>
        )}
      </div>
      {/* Thumbnails */}
      {images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto">
          {images.map((img, i) => (
            <button key={img.id} onClick={() => setActive(i)}
              className={`shrink-0 w-16 h-16 overflow-hidden border-2 transition-colors ${i === active ? 'border-accent' : 'border-transparent'}`}>
              <img src={img.url} alt="" className="w-full h-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
