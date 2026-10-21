'use client'

import { AlertCircleIcon, CircleCheckIcon } from 'lucide-react'
import Link from 'next/link'
import { useRef, useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { ledgerService } from '@/lib/ledger/service'
import { LedgerError } from '@/lib/ledger/types'
import { validateEmail } from '@/lib/validation'
import { AuthHeading } from './auth-card'
import { PasswordInput } from './password-input'

export function LoginForm({ nextPath, registrationComplete = false }: { nextPath: string; registrationComplete?: boolean }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  const [formError, setFormError] = useState<string>()
  const [pending, setPending] = useState(false)
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const next = {
      email: validateEmail(email),
      password: password ? undefined : 'Enter your password.',
    }
    setErrors(next)
    setFormError(undefined)
    if (next.email) return emailRef.current?.focus()
    if (next.password) return passwordRef.current?.focus()

    setPending(true)
    try {
      await ledgerService.signIn({ email, password, remember })
      window.location.replace(nextPath)
    } catch (error) {
      setFormError(error instanceof LedgerError ? error.message : 'Something went wrong. Please try again.')
      setPending(false)
      passwordRef.current?.select()
    }
  }

  return (
    <>
      <AuthHeading title="Sign in to LedgerChain" description="Welcome back. Enter your work email to continue." />

      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-6">
        {registrationComplete && (
          <Alert className="animate-fade border-success/30 bg-success-soft text-success">
            <CircleCheckIcon aria-hidden="true" />
            <AlertTitle>Account created</AlertTitle>
            <AlertDescription className="text-success">Sign in with your email and password to continue.</AlertDescription>
          </Alert>
        )}
        {formError && (
          <Alert variant="destructive" className="animate-fade">
            <AlertCircleIcon aria-hidden="true" />
            <AlertTitle>Couldn&apos;t sign you in</AlertTitle>
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}

        <FieldGroup>
          <Field data-invalid={!!errors.email || undefined}>
            <FieldLabel htmlFor="login-email">Work email</FieldLabel>
            <Input
              ref={emailRef}
              id="login-email"
              type="email"
              autoComplete="email"
              inputMode="email"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={!!errors.email || undefined}
              aria-describedby={errors.email ? 'login-email-error' : undefined}
              className="h-10"
            />
            {errors.email && <FieldError id="login-email-error">{errors.email}</FieldError>}
          </Field>

          <Field data-invalid={!!errors.password || undefined}>
            <div className="flex items-center justify-between gap-2">
              <FieldLabel htmlFor="login-password">Password</FieldLabel>
              <Link
                href="/forgot-password"
                className="rounded-sm text-sm font-medium text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
              >
                Forgot password?
              </Link>
            </div>
            <PasswordInput
              ref={passwordRef}
              id="login-password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={!!errors.password || undefined}
              aria-describedby={errors.password ? 'login-password-error' : undefined}
              className="h-10"
            />
            {errors.password && <FieldError id="login-password-error">{errors.password}</FieldError>}
          </Field>

          <Field orientation="horizontal">
            <Checkbox id="login-remember" checked={remember} onCheckedChange={(checked) => setRemember(checked)} />
            <FieldLabel htmlFor="login-remember" className="font-normal">
              Keep me signed in on this device
            </FieldLabel>
          </Field>
        </FieldGroup>

        <Button type="submit" size="lg" className="h-10" disabled={pending}>
          {pending && <Spinner data-icon="inline-start" />}
          {pending ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        New to LedgerChain?{' '}
        <Link href="/signup" className="font-medium text-primary underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>

    </>
  )
}
