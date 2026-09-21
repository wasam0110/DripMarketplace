import { useState, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ImagePlus, X, Loader2 } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { toast } from '@/components/ui/Toast'
import { useCreateProduct } from '@/hooks/useSeller'
import { client } from '@/api/client'
import { getErrorMessage } from '@/utils/errorHandler'

const MAX_IMAGES = 3
const MAX_SIZE_MB = 2

const schema = z.object({
  name:        z.string().min(2).max(200),
  description: z.string().min(10).max(5000),
  price:       z.coerce.number().min(100).max(500_000),
  sale_price:  z.coerce.number().min(100).max(500_000).optional().or(z.literal('')),
  colour:      z.string().min(1),
  size_value:  z.string().min(1),
  stock:       z.coerce.number().min(0),
  sku:         z.string().max(100).optional(),
})
type FormValues = z.infer<typeof schema>

interface ImagePreview {
  file:      File
  preview:   string
  url?:      string
  uploading: boolean
  error?:    string
}

export function ProductForm({ onSuccess }: { onSuccess?: () => void }) {
  const create   = useCreateProduct()
  const inputRef = useRef<HTMLInputElement>(null)
  const [images, setImages] = useState<ImagePreview[]>([])

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { colour: 'Black', size_value: 'One Size', stock: 1 },
  })

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    const remaining = MAX_IMAGES - images.length
    const toAdd = files.slice(0, remaining)

    for (const file of toAdd) {
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        toast.error(`${file.name}: only JPEG, PNG, or WebP allowed`)
        continue
      }
      if (file.size > MAX_SIZE_MB * 1024 * 1024) {
        toast.error(`${file.name}: must be under ${MAX_SIZE_MB} MB`)
        continue
      }
      const preview: ImagePreview = { file, preview: URL.createObjectURL(file), uploading: true }
      setImages(prev => [...prev, preview])
      uploadImage(file, preview.preview)
    }
    e.target.value = ''
  }

  async function uploadImage(file: File, previewId: string) {
    try {
      const fd = new FormData()
      fd.append('image', file)
      const res = await client.post<{ url: string }>('/seller/products/upload-image', fd)
      setImages(prev => prev.map(img =>
        img.preview === previewId ? { ...img, uploading: false, url: res.data.url } : img
      ))
    } catch {
      setImages(prev => prev.map(img =>
        img.preview === previewId
          ? { ...img, uploading: false, error: 'Upload failed — image will be skipped' }
          : img
      ))
    }
  }

  function removeImage(previewId: string) {
    setImages(prev => {
      const img = prev.find(i => i.preview === previewId)
      if (img) URL.revokeObjectURL(img.preview)
      return prev.filter(i => i.preview !== previewId)
    })
  }

  const onSubmit = async (data: FormValues) => {
    if (images.some(i => i.uploading)) {
      toast.error('Please wait for images to finish uploading.')
      return
    }
    try {
      const imageUrls = images.filter(i => i.url).map(i => i.url!)
      await create.mutateAsync({
        name:         data.name,
        description:  data.description,
        price:        data.price * 100,
        sale_price:   data.sale_price ? Number(data.sale_price) * 100 : null,
        is_published: false,
        images:       imageUrls,
        variants: [{
          colour:     data.colour,
          size_value: data.size_value,
          size_type:  'one_size',
          stock:      data.stock,
          sku:        data.sku || null,
        }],
      })
      toast.success('Product created as draft.')
      images.forEach(i => URL.revokeObjectURL(i.preview))
      setImages([])
      reset()
      onSuccess?.()
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  const anyUploading = images.some(i => i.uploading)

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">

      {/* Image upload */}
      <div className="flex flex-col gap-2">
        <label className="text-[10px] font-bold tracking-widest text-muted uppercase">
          Product images <span className="normal-case font-normal">({images.length}/{MAX_IMAGES})</span>
        </label>

        <div className="flex gap-3 flex-wrap">
          {images.map((img, idx) => (
            <div key={img.preview}
              className="relative w-24 h-28 bg-card border border-border overflow-hidden shrink-0">
              <img src={img.preview} alt="" className="w-full h-full object-cover" />

              {img.uploading && (
                <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                  <Loader2 size={16} className="animate-spin text-white" />
                </div>
              )}

              {img.error && !img.uploading && (
                <div className="absolute bottom-0 inset-x-0 bg-danger/80 px-1 py-0.5">
                  <p className="text-[9px] text-white leading-tight">Upload failed</p>
                </div>
              )}

              {!img.uploading && (
                <button type="button" onClick={() => removeImage(img.preview)}
                  className="absolute top-1 right-1 w-5 h-5 bg-black/70 flex items-center justify-center hover:bg-danger transition-colors">
                  <X size={10} className="text-white" />
                </button>
              )}

              <span className="absolute bottom-1 left-1 bg-black/70 text-white text-[9px] font-mono px-1">
                {idx === 0 ? 'MAIN' : `0${idx + 1}`}
              </span>
            </div>
          ))}

          {images.length < MAX_IMAGES && (
            <button type="button" onClick={() => inputRef.current?.click()}
              className="w-24 h-28 border border-dashed border-border flex flex-col items-center justify-center gap-2 text-muted hover:border-accent hover:text-accent transition-colors shrink-0">
              <ImagePlus size={18} />
              <span className="text-[10px] font-bold tracking-wide">ADD</span>
            </button>
          )}
        </div>

        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp"
          multiple className="hidden" onChange={handleFileSelect} />

        <p className="text-[10px] text-muted">
          JPEG, PNG or WebP · Max {MAX_SIZE_MB} MB each · First image is the main photo
        </p>
      </div>

      {/* Fields */}
      <Input label="Product name" error={errors.name?.message} {...register('name')} placeholder="Orbit Heavyweight Tee" />

      <div className="flex flex-col gap-1">
        <label className="text-[10px] font-bold tracking-widest text-muted uppercase">Description</label>
        <textarea {...register('description')} rows={4} className="input-base resize-none"
          placeholder="Describe the piece, fit, and materials." />
        {errors.description && <p className="text-xs text-danger">{errors.description.message}</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Input label="Price (PKR)"           type="number" error={errors.price?.message}      {...register('price')} />
        <Input label="Sale price (optional)"  type="number" error={errors.sale_price?.message} {...register('sale_price')} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Input label="Colour" error={errors.colour?.message}     {...register('colour')}     placeholder="Black" />
        <Input label="Size"   error={errors.size_value?.message} {...register('size_value')} placeholder="One Size / M / 32" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Input label="Stock"          type="number" error={errors.stock?.message} {...register('stock')} />
        <Input label="SKU (optional)"              error={errors.sku?.message}   {...register('sku')}   placeholder="ORB-TEE-001" />
      </div>

      <Button type="submit" loading={create.isPending || anyUploading} className="mt-2">
        {anyUploading ? 'Uploading images…' : 'Create product'}
      </Button>
    </form>
  )
}