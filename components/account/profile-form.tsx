'use client'

import { AlertCircleIcon, PencilIcon } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { toast } from 'sonner'
import { CopyButton } from '@/components/ledger/copy-button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { formatDate } from '@/lib/ledger/format'
import { ledgerService } from '@/lib/ledger/service'
import { LedgerError, type AccountProfile, type ProfileUpdate } from '@/lib/ledger/types'
import { validateEmail, validateRequired } from '@/lib/validation'
import { SettingRow, SettingsSection } from './settings-section'

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
}

const toDraft = (p: AccountProfile): Required<ProfileUpdate> => ({
  name: p.name,
  company: p.company,
  email: p.email,
  phone: p.phone ?? '',
})

export function ProfileForm({ initialProfile, completeSetup = false }: { initialProfile: AccountProfile; completeSetup?: boolean }) {
  const router = useRouter()
  const [profile, setProfile] = useState(initialProfile)
  const [editing, setEditing] = useState(completeSetup)
  const [draft, setDraft] = useState(() => toDraft(initialProfile))
  const [errors, setErrors] = useState<Partial<Record<keyof ProfileUpdate, string>>>({})
  const [saveError, setSaveError] = useState<string>()
  const [partialSave, setPartialSave] = useState(false)
  const [pending, setPending] = useState(false)

  const set = (key: keyof ProfileUpdate) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setDraft((d) => ({ ...d, [key]: e.target.value }))

  function startEditing() {
    setDraft(toDraft(profile))
    setErrors({})
    setSaveError(undefined)
    setPartialSave(false)
    setEditing(true)
    requestAnimationFrame(() => document.getElementById('profile-name')?.focus())
  }

  function cancel() {
    setEditing(false)
    setErrors({})
    setSaveError(undefined)
    setPartialSave(false)
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const next = {
      name: validateRequired(draft.name, 'full name'),
      company: validateRequired(draft.company, 'business name'),
      email: validateEmail(draft.email),
    }
    setErrors(next)
    const firstInvalid = (Object.keys(next) as (keyof typeof next)[]).find((key) => next[key])
    if (firstInvalid) return document.getElementById(`profile-${firstInvalid}`)?.focus()

    setPending(true)
    setSaveError(undefined)
    setPartialSave(false)
    try {
      const saved = await ledgerService.updateProfile({
        name: draft.name.trim(),
        company: draft.company.trim(),
        email: draft.email.trim(),
        phone: draft.phone.trim() || undefined,
      })
      setProfile(saved)
      setEditing(false)
      setPartialSave(false)
      toast.success('Profile saved', { description: 'Your details are up to date.' })
      if (completeSetup) router.replace('/')
    } catch (error) {
      setPartialSave(error instanceof LedgerError && error.committed)
      setSaveError(error instanceof LedgerError ? error.message : 'Something went wrong. Please try again.')
    } finally {
      setPending(false)
    }
  }

  const fieldProps = (key: keyof ProfileUpdate) => ({
    id: `profile-${key}`,
    value: draft[key],
    onChange: set(key),
    'aria-invalid': !!errors[key] || undefined,
    'aria-describedby': errors[key] ? `profile-${key}-error` : undefined,
  })

  return (
    <div className="flex flex-col gap-8 lg:gap-10">
      <div className="flex flex-col gap-4 rounded-xl border bg-card p-4 sm:flex-row sm:items-center md:p-5">
        <Avatar className="size-14">
          <AvatarFallback className="bg-accent text-lg font-semibold text-accent-foreground">
            {initials(profile.name)}
          </AvatarFallback>
        </Avatar>
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <p className="truncate text-lg font-semibold">{profile.name}</p>
          <p className="truncate text-sm text-muted-foreground">
            {profile.role} · {profile.company}
          </p>
        </div>
        {!editing && (
          <Button variant="outline" onClick={startEditing} className="self-start sm:self-center">
            <PencilIcon data-icon="inline-start" aria-hidden="true" />
            Edit profile
          </Button>
        )}
      </div>

      <SettingsSection
        id="details"
        title="Personal details"
        description="Shown to people you pay and on records you create."
      >
        {editing ? (
          <form noValidate onSubmit={onSubmit} className="flex animate-fade flex-col gap-6 p-4 md:p-5">
            {saveError && (
              <Alert variant="destructive" className="animate-fade">
                <AlertCircleIcon aria-hidden="true" />
                <AlertTitle>{partialSave ? 'Profile partially saved' : 'Profile not saved'}</AlertTitle>
                <AlertDescription>{saveError}</AlertDescription>
              </Alert>
            )}
            <FieldGroup>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field data-invalid={!!errors.name || undefined}>
                  <FieldLabel htmlFor="profile-name">Full name</FieldLabel>
                  <Input {...fieldProps('name')} autoComplete="name" />
                  {errors.name && <FieldError id="profile-name-error">{errors.name}</FieldError>}
                </Field>
                <Field data-invalid={!!errors.company || undefined}>
                  <FieldLabel htmlFor="profile-company">Business name</FieldLabel>
                  <Input {...fieldProps('company')} autoComplete="organization" />
                  {errors.company && <FieldError id="profile-company-error">{errors.company}</FieldError>}
                </Field>
                <Field data-invalid={!!errors.email || undefined}>
                  <FieldLabel htmlFor="profile-email">Work email</FieldLabel>
                  <Input {...fieldProps('email')} type="email" autoComplete="email" disabled />
                  {errors.email ? (
                    <FieldError id="profile-email-error">{errors.email}</FieldError>
                  ) : (
                    <FieldDescription>Email changes are not supported by the current backend.</FieldDescription>
                  )}
                </Field>
                <Field>
                  <FieldLabel htmlFor="profile-phone">
                    Phone <span className="font-normal text-muted-foreground">(optional)</span>
                  </FieldLabel>
                  <Input {...fieldProps('phone')} type="tel" inputMode="tel" autoComplete="tel" />
                </Field>
              </div>
            </FieldGroup>
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button type="button" variant="ghost" onClick={cancel} disabled={pending}>
                Cancel
              </Button>
              <Button type="submit" disabled={pending}>
                {pending && <Spinner data-icon="inline-start" />}
                {pending ? 'Saving…' : 'Save changes'}
              </Button>
            </div>
          </form>
        ) : (
          <dl className="animate-fade">
            {[
              ['Full name', profile.name],
              ['Business name', profile.company],
              ['Work email', profile.email],
              ['Phone', profile.phone || 'Not added'],
            ].map(([label, value]) => (
              <div key={label} className="grid gap-1 border-b p-4 last:border-b-0 sm:grid-cols-[10rem_minmax(0,1fr)] md:px-5">
                <dt className="text-sm text-muted-foreground">{label}</dt>
                <dd className="text-sm font-medium break-words">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </SettingsSection>

      <SettingsSection
        id="account"
        title="Account"
        description="Use your account ID when contacting support."
      >
        <SettingRow
          title="Account ID"
          description={<span className="font-mono text-foreground">{profile.id}</span>}
        >
          <CopyButton value={profile.id} label="Copy account ID" />
        </SettingRow>
        <SettingRow title="Role" description={profile.role} />
        <SettingRow title="Member since" description={formatDate(profile.memberSince)} />
      </SettingsSection>
    </div>
  )
}
