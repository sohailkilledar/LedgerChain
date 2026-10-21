'use client'

import { AlertCircleIcon, ArrowLeftIcon, MailCheckIcon } from 'lucide-react'
import Link from 'next/link'
import { useRef, useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { ledgerService } from '@/lib/ledger/service'
import { LedgerError } from '@/lib/ledger/types'
import { validateEmail } from '@/lib/validation'
import { AuthHeading } from './auth-card'

export function ForgotPasswordForm() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string>()
  const [pending, setPending] = useState(false)
  const [sentTo, setSentTo] = useState<string>()
  const [resetToken, setResetToken] = useState<string>()
  const [requestError, setRequestError] = useState<string>()
  const inputRef = useRef<HTMLInputElement>(null)

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const message = validateEmail(email)
    setError(message)
    if (message) return inputRef.current?.focus()
    setPending(true)
    setRequestError(undefined)
    try {
      const result = await ledgerService.requestPasswordReset(email.trim())
      setResetToken(result.development_token)
      setSentTo(email.trim())
    } catch (error) {
      setRequestError(error instanceof LedgerError ? error.message : 'We could not process the request. Please try again.')
    } finally {
      setPending(false)
    }
  }

  if (sentTo) {
    return (
      <div role="status" className="flex flex-col gap-6">
        <AuthHeading
          icon={MailCheckIcon}
          tone="success"
          title="Check your email"
          description={
            <>
              If an account exists for <span className="font-medium text-foreground">{sentTo}</span>, we&apos;ll send a
              link to reset your password. It expires in 30 minutes.
            </>
          }
        />
        {resetToken ? (
          <Button size="lg" className="h-10" render={<Link href={`/reset-password?token=${encodeURIComponent(resetToken)}`} />} nativeButton={false}>
            Continue with development reset token
          </Button>
        ) : (
          <p className="text-sm text-muted-foreground">
            If email delivery is configured, use the reset link sent to this address. This backend does not currently send email.
          </p>
        )}
        <Button variant="ghost" size="lg" className="h-10" onClick={() => setSentTo(undefined)}>
          Use a different email
        </Button>
      </div>
    )
  }

  return (
    <>
      <AuthHeading
        title="Reset your password"
        description="Enter the email you use for LedgerChain and we'll send you a reset link."
      />
      {requestError && (
        <Alert variant="destructive">
          <AlertCircleIcon aria-hidden="true" />
          <AlertDescription>{requestError}</AlertDescription>
        </Alert>
      )}
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-6">
        <FieldGroup>
          <Field data-invalid={!!error || undefined}>
            <FieldLabel htmlFor="forgot-email">Work email</FieldLabel>
            <Input
              ref={inputRef}
              id="forgot-email"
              type="email"
              inputMode="email"
              autoComplete="email"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={!!error || undefined}
              aria-describedby={error ? 'forgot-email-error' : 'forgot-email-hint'}
              className="h-10"
            />
            {error ? (
              <FieldError id="forgot-email-error">{error}</FieldError>
            ) : (
              <FieldDescription id="forgot-email-hint">For your security, we won&apos;t confirm whether an account exists.</FieldDescription>
            )}
          </Field>
        </FieldGroup>
        <Button type="submit" size="lg" className="h-10" disabled={pending}>
          {pending && <Spinner data-icon="inline-start" />}
          {pending ? 'Sending link…' : 'Send reset link'}
        </Button>
      </form>
      <BackToLogin />
    </>
  )
}

export function BackToLogin() {
  return (
    <Button variant="ghost" className="self-center text-muted-foreground" render={<Link href="/login" />} nativeButton={false}>
      <ArrowLeftIcon data-icon="inline-start" aria-hidden="true" />
      Back to sign in
    </Button>
  )
}
