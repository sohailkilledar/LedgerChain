'use client'

import { AlertCircleIcon } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { ledgerService } from '@/lib/ledger/service'
import { LedgerError } from '@/lib/ledger/types'
import { validateConfirmPassword, validateEmail, validateNewPassword } from '@/lib/validation'
import { AuthHeading } from './auth-card'
import { PasswordInput, PasswordStrengthMeter } from './password-input'

type FieldName = 'email' | 'password' | 'confirm' | 'terms'
const order: FieldName[] = ['email', 'password', 'confirm', 'terms']

export function SignupForm() {
  const router = useRouter()
  const [values, setValues] = useState({ email: '', password: '', confirm: '' })
  const [terms, setTerms] = useState(false)
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({})
  const [formError, setFormError] = useState<string>()
  const [pending, setPending] = useState(false)

  const set = (key: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }))

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const next: Partial<Record<FieldName, string>> = {
      email: validateEmail(values.email),
      password: validateNewPassword(values.password),
      confirm: validateConfirmPassword(values.password, values.confirm),
      terms: terms ? undefined : 'Please agree to the terms to create your account.',
    }
    setErrors(next)
    setFormError(undefined)
    const firstInvalid = order.find((key) => next[key])
    if (firstInvalid) {
      document.getElementById(`signup-${firstInvalid}`)?.focus()
      return
    }

    setPending(true)
    try {
      await ledgerService.signUp({ email: values.email.trim(), password: values.password })
      router.push('/login?registered=1')
    } catch (error) {
      setFormError(error instanceof LedgerError ? error.message : 'Something went wrong. Please try again.')
      setPending(false)
    }
  }

  const fieldProps = (key: FieldName) => ({
    id: `signup-${key}`,
    'aria-invalid': !!errors[key] || undefined,
    'aria-describedby': errors[key] ? `signup-${key}-error` : undefined,
  })

  return (
    <>
      <AuthHeading
        title="Create your account"
        description="Create your account with your work email and password."
      />

      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-6">
        {formError && (
          <Alert variant="destructive" className="animate-fade">
            <AlertCircleIcon aria-hidden="true" />
            <AlertTitle>Couldn&apos;t create your account</AlertTitle>
            <AlertDescription>
              {formError}{' '}
              <Link href="/login" className="font-medium underline underline-offset-4">
                Sign in
              </Link>
            </AlertDescription>
          </Alert>
        )}

        <FieldGroup>
          <Field data-invalid={!!errors.email || undefined}>
            <FieldLabel htmlFor="signup-email">Work email</FieldLabel>
            <Input
              {...fieldProps('email')}
              type="email"
              inputMode="email"
              autoComplete="email"
              placeholder="name@company.com"
              value={values.email}
              onChange={set('email')}
              className="h-10"
            />
            {errors.email && <FieldError id="signup-email-error">{errors.email}</FieldError>}
          </Field>

          <Field data-invalid={!!errors.password || undefined}>
            <FieldLabel htmlFor="signup-password">Password</FieldLabel>
            <PasswordInput
              {...fieldProps('password')}
              aria-describedby={['signup-password-strength', errors.password && 'signup-password-error']
                .filter(Boolean)
                .join(' ')}
              autoComplete="new-password"
              value={values.password}
              onChange={set('password')}
              className="h-10"
            />
            <PasswordStrengthMeter id="signup-password-strength" password={values.password} />
            {errors.password && <FieldError id="signup-password-error">{errors.password}</FieldError>}
          </Field>

          <Field data-invalid={!!errors.confirm || undefined}>
            <FieldLabel htmlFor="signup-confirm">Confirm password</FieldLabel>
            <PasswordInput
              {...fieldProps('confirm')}
              autoComplete="new-password"
              value={values.confirm}
              onChange={set('confirm')}
              className="h-10"
            />
            {errors.confirm && <FieldError id="signup-confirm-error">{errors.confirm}</FieldError>}
          </Field>

          <Field orientation="horizontal" data-invalid={!!errors.terms || undefined} className="items-start">
            <Checkbox
              {...fieldProps('terms')}
              checked={terms}
              onCheckedChange={(checked) => setTerms(checked)}
              className="mt-0.5"
            />
            <div className="flex flex-col gap-1.5">
              <FieldLabel htmlFor="signup-terms" className="font-normal leading-snug">
                I agree to the LedgerChain Terms of Service and Privacy Policy.
              </FieldLabel>
              {errors.terms && <FieldError id="signup-terms-error">{errors.terms}</FieldError>}
            </div>
          </Field>
        </FieldGroup>

        <Button type="submit" size="lg" className="h-10" disabled={pending}>
          {pending && <Spinner data-icon="inline-start" />}
          {pending ? 'Creating account…' : 'Create account'}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{' '}
        <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>

    </>
  )
}
