'use client'

import { AlertCircleIcon, ArrowRightIcon } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'
import { toast } from 'sonner'
import { ThemeSelector } from '@/components/theme/theme-selector'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { Switch } from '@/components/ui/switch'
import { ledgerService } from '@/lib/ledger/service'
import { LedgerError, type AccountPreferences } from '@/lib/ledger/types'
import { SettingRow, SettingsSection } from './settings-section'

const timeZones = [
  { value: 'Asia/Kolkata', label: 'India (IST, UTC+5:30)' },
  { value: 'Asia/Dubai', label: 'Gulf (GST, UTC+4)' },
  { value: 'Europe/London', label: 'London (UK time)' },
  { value: 'America/New_York', label: 'New York (US Eastern)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT, UTC+8)' },
]

const dateFormats: { value: AccountPreferences['dateFormat']; label: string }[] = [
  { value: 'dmy', label: '27 Sep 2026' },
  { value: 'mdy', label: 'Sep 27, 2026' },
  { value: 'iso', label: '2026-09-27' },
]

type BooleanKey = {
  [K in keyof AccountPreferences]: AccountPreferences[K] extends boolean ? K : never
}[keyof AccountPreferences]

export function SettingsForm({ initialPreferences }: { initialPreferences: AccountPreferences }) {
  const [saved, setSaved] = useState(initialPreferences)
  const [prefs, setPrefs] = useState(initialPreferences)
  const [pending, setPending] = useState(false)
  const [saveError, setSaveError] = useState<string>()
  const [partialSave, setPartialSave] = useState(false)

  const dirty = JSON.stringify(prefs) !== JSON.stringify(saved)
  const toggle = (key: BooleanKey) => (checked: boolean) => setPrefs((p) => ({ ...p, [key]: checked }))

  async function save() {
    setPending(true)
    setSaveError(undefined)
    setPartialSave(false)
    try {
      const next = await ledgerService.updatePreferences(prefs)
      setSaved(next)
      setPrefs(next)
      setPartialSave(false)
      toast.success('Settings saved')
    } catch (error) {
      setPartialSave(error instanceof LedgerError && error.committed)
      setSaveError(error instanceof LedgerError ? error.message : 'Something went wrong. Please try again.')
    } finally {
      setPending(false)
    }
  }

  const switchRow = (key: BooleanKey, title: string, description: string) => (
    <SettingRow key={key} title={title} description={description} htmlFor={`setting-${key}`}>
      <Switch id={`setting-${key}`} checked={prefs[key]} onCheckedChange={toggle(key)} />
    </SettingRow>
  )

  return (
    <div className="flex flex-col gap-8 pb-24 lg:gap-10">
      <SettingsSection
        id="appearance"
        title="Appearance"
        description="Choose how LedgerChain looks on this device. Applied instantly."
      >
        <div className="p-4 md:p-5">
          <ThemeSelector />
        </div>
      </SettingsSection>

      <SettingsSection id="preferences" title="Preferences" description="How dates and times appear across your records.">
        <SettingRow title="Time zone" description="Used for activity timestamps." htmlFor="setting-timezone">
          <Select
            items={timeZones}
            value={prefs.timeZone}
            onValueChange={(value) => value && setPrefs((p) => ({ ...p, timeZone: String(value) }))}
          >
            <SelectTrigger id="setting-timezone" className="w-full min-w-56 sm:w-auto">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {timeZones.map((zone) => (
                <SelectItem key={zone.value} value={zone.value}>
                  {zone.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </SettingRow>
        <SettingRow title="Date format" htmlFor="setting-date-format">
          <Select
            items={dateFormats}
            value={prefs.dateFormat}
            onValueChange={(value) =>
              value && setPrefs((p) => ({ ...p, dateFormat: value as AccountPreferences['dateFormat'] }))
            }
          >
            <SelectTrigger id="setting-date-format" className="w-full min-w-40 sm:w-auto">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {dateFormats.map((format) => (
                <SelectItem key={format.value} value={format.value}>
                  {format.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </SettingRow>
        {switchRow(
          'showTechnicalByDefault',
          'Show technical details by default',
          'Open the ledger-level information on every record without an extra click.',
        )}
      </SettingsSection>

      <SettingsSection id="notifications" title="Notification preferences" description="Save your preferences for notification categories. Delivery is not currently wired to an email provider.">
        {switchRow('notifyPayments', 'Payments', 'When a payment you sent or received is confirmed or fails.')}
        {switchRow('notifySecurity', 'Security alerts', 'New sign-ins and password changes. Recommended.')}
        {switchRow('notifyProductUpdates', 'Product updates', 'Preference is saved to your account; delivery is not currently active.')}
      </SettingsSection>

      <SettingsSection id="privacy" title="Privacy" description="Control how your data is used beyond your records.">
        {switchRow(
          'shareUsageData',
          'Share anonymous usage data',
          'Helps us improve LedgerChain. Never includes amounts, names, or record contents.',
        )}
        <SettingRow
          title="Your ledger records"
          description="Confirmed records are permanent by design and can't be deleted — only corrected with a new entry."
        >
          <Button variant="ghost" size="sm" render={<Link href="/how-it-works" />} nativeButton={false}>
            Learn why
          </Button>
        </SettingRow>
      </SettingsSection>

      <SettingsSection id="account" title="Account" description="Profile and sign-in.">
        <SettingRow title="Profile" description="Name, business, email, and account ID.">
          <Button variant="outline" size="sm" render={<Link href="/profile" />} nativeButton={false}>
            Manage
            <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
          </Button>
        </SettingRow>
      </SettingsSection>

      <div
        className={
          dirty || saveError
            ? 'fixed inset-x-0 bottom-0 z-30 animate-enter border-t bg-card/95 backdrop-blur lg:left-64'
            : 'sr-only'
        }
      >
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 md:px-8">
          {saveError && (
            <Alert variant="destructive" className="animate-fade">
              <AlertCircleIcon aria-hidden="true" />
              <AlertTitle>{partialSave ? 'Settings partially saved' : 'Settings not saved'}</AlertTitle>
              <AlertDescription>{saveError}</AlertDescription>
            </Alert>
          )}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-medium" aria-live="polite">
              {dirty ? 'You have unsaved changes' : ''}
            </p>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  className="flex-1 sm:flex-none"
                  disabled={pending || !dirty}
                  onClick={() => {
                    setPrefs(saved)
                    setSaveError(undefined)
                    setPartialSave(false)
                  }}
                >
                  Discard
                </Button>
                <Button className="flex-1 sm:flex-none" disabled={pending || !dirty} onClick={save}>
                  {pending && <Spinner data-icon="inline-start" />}
                  {pending ? 'Saving…' : 'Save changes'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
