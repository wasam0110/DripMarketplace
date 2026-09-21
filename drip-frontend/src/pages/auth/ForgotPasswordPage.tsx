import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '@/api/auth.api'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { getErrorMessage } from '@/utils/errorHandler'

const schema = z.object({ email: z.string().email() })

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)
  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) })
  const mutation = useMutation({ mutationFn: authApi.forgotPassword, onSuccess: () => setSent(true) })

  if (sent) return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="text-center flex flex-col gap-4 max-w-sm">
        <p className="text-accent text-4xl font-bold font-mono">✓</p>
        <h2 className="font-bold text-xl">Check your email.</h2>
        <p className="text-muted text-sm">If that address is in our system, a reset link is on its way.</p>
        <Link to="/login" className="text-xs text-muted hover:text-white">Back to sign in</Link>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm flex flex-col gap-8">
        <div>
          <Link to="/" className="font-mono font-bold text-2xl">DRIP<span className="text-accent">.</span></Link>
          <h1 className="text-2xl font-bold mt-6">Reset password.</h1>
          <p className="text-muted text-sm mt-1">Enter your email and we'll send a reset link.</p>
        </div>
        <form onSubmit={handleSubmit(d => mutation.mutate(d as { email: string }))} className="flex flex-col gap-4">
          <Input label="Email" type="email" error={errors.email?.message} {...register('email')} />
          {mutation.error && <p className="text-xs text-danger">{getErrorMessage(mutation.error)}</p>}
          <Button type="submit" loading={mutation.isPending} className="w-full justify-center">Send reset link</Button>
        </form>
        <Link to="/login" className="text-xs text-muted hover:text-white text-center">Back to sign in</Link>
      </div>
    </div>
  )
}
