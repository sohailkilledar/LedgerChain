'use client'

import { AlertCircleIcon, CircleCheckIcon } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Spinner } from '@/components/ui/spinner'
import { ledgerService } from '@/lib/ledger/service'
import { validateConfirmPassword, validateNewPassword } from '@/lib/validation'
import { AuthHeading } from './auth-card'
import { BackToLogin } from './forgot-password-form'
import { PasswordInput, PasswordStrengthMeter } from './password-input'

export function ResetPasswordForm({ token }: { token?: string }) {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<{ password?: string; confirm?: string }>({})
  const [pending, setPending] = useState(false)
  const [done, setDone] = useState(false)
  const [requestError, setRequestError] = useState<string>()

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const next = { password: validateNewPassword(password), confirm: validateConfirmPassword(password, confirm) }
    setErrors(next)
    if (next.password) return document.getElementById('reset-password')?.focus()
    if (next.confirm) return document.getElementById('reset-confirm')?.focus()
    if (!token) {
      setRequestError('This reset page needs a valid token from your reset link.')
      return
    }
    setPending(true)
    setRequestError(undefined)
    try {
      await ledgerService.resetPassword({ password, token })
      setDone(true)
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : 'We could not update your password. Please try again.')
    } finally {
      setPending(false)
    }
  }

  if (done) {
    return (
      <div role="status" className="flex flex-col gap-6">
        <AuthHeading
          icon={CircleCheckIcon}
          tone="success"
          title="Password updated"
          description="Your new password is ready. For your security, you've been signed out of other devices."
        />
        <Button size="lg" className="h-10" render={<Link href="/login" />} nativeButton={false}>
          Sign in with new password
        </Button>
      </div>
    )
  }

  return (
    <>
      <AuthHeading title="Choose a new password" description="Pick something you haven't used for LedgerChain before." />
      {requestError && (
        <Alert variant="destructive">
          <AlertCircleIcon aria-hidden="true" />
          <AlertDescription>{requestError}</AlertDescription>
        </Alert>
      )}
      {!token && (
        <Alert>
          <AlertDescription>Open a valid reset link to provide its one-time token before choosing a new password.</AlertDescription>
        </Alert>
      )}
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-6">
        <FieldGroup>
          <Field data-invalid={!!errors.password || undefined}>
            <FieldLabel htmlFor="reset-password">New password</FieldLabel>
            <PasswordInput
              id="reset-password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={!!errors.password || undefined}
              aria-describedby={['reset-strength', errors.password && 'reset-password-error'].filter(Boolean).join(' ')}
              className="h-10"
            />
            <PasswordStrengthMeter id="reset-strength" password={password} />
            {errors.password && <FieldError id="reset-password-error">{errors.password}</FieldError>}
          </Field>
          <Field data-invalid={!!errors.confirm || undefined}>
            <FieldLabel htmlFor="reset-confirm">Confirm new password</FieldLabel>
            <PasswordInput
              id="reset-confirm"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              aria-invalid={!!errors.confirm || undefined}
              aria-describedby={errors.confirm ? 'reset-confirm-error' : undefined}
              className="h-10"
            />
            {errors.confirm && <FieldError id="reset-confirm-error">{errors.confirm}</FieldError>}
          </Field>
        </FieldGroup>
        <Button type="submit" size="lg" className="h-10" disabled={pending || !token}>
          {pending && <Spinner data-icon="inline-start" />}
          {pending ? 'Updating password…' : 'Update password'}
        </Button>
      </form>
      <BackToLogin />
    </>
  )
}
