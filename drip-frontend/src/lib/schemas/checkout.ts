import { z } from 'zod'

const phone = /^(\+92|0092|0)?3[0-9]{9}$/

export const contactSchema = z.object({
  recipient_name: z.string().min(2).max(200).transform(s => s.trim()),
  email:          z.string().email().max(254).transform(s => s.toLowerCase()).optional(),
  phone:          z.string().regex(phone, 'Enter a valid Pakistani number (03XXXXXXXXX)'),
})
export const shippingSchema = z.object({
  street:   z.string().min(10, 'Street must be at least 10 characters').max(500),
  city:     z.string().min(1, 'City is required'),
  province: z.string().min(1, 'Province is required'),
  notes:    z.string().max(300).optional(),
})
export const paymentSchema = z.object({
  method: z.enum(['payfast', 'cod']),
})
export const checkoutSchema = contactSchema.merge(shippingSchema).merge(paymentSchema)
export type CheckoutFormValues = z.infer<typeof checkoutSchema>
