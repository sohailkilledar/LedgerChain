'use client'

import { ArrowRightIcon } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { InputGroup, InputGroupAddon, InputGroupInput, InputGroupText } from '@/components/ui/input-group'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { purposeLabels } from '@/lib/ledger/format'
import { amountMinorUnits, exactMoney } from '@/lib/ledger/api-client'
import type { PaymentDraft, PaymentPurpose } from '@/lib/ledger/types'

type FormValues = {
  recipientAccount: string
  amount: string
  purpose: PaymentPurpose | ''
  note: string
}

type Errors = Partial<Record<keyof FormValues, string>>

const purposeItems = (Object.keys(purposeLabels) as PaymentPurpose[]).map((value) => ({
  value,
  label: purposeLabels[value],
}))

const ACCOUNT_PATTERN = /^\d{9,18}$/

function validate(values: FormValues, availableBalance: string): Errors {
  const errors: Errors = {}
  const account = values.recipientAccount.trim().replace(/\s/g, '')
  if (!account) {
    errors.recipientAccount = 'Enter a LedgerChain account number.'
  } else if (!ACCOUNT_PATTERN.test(account)) {
    errors.recipientAccount = 'Enter a 9–18 digit LedgerChain account number.'
  }
  if (!values.amount) {
    errors.amount = 'Enter how much you want to send.'
  } else if (!/^\d+(?:\.\d{1,2})?$/.test(values.amount)) {
    errors.amount = 'Enter a valid amount with no more than two decimal places.'
  } else if (amountMinorUnits(values.amount) <= 0n) {
    errors.amount = 'Enter an amount greater than ₹0.'
  } else if (amountMinorUnits(values.amount) > amountMinorUnits(availableBalance)) {
    errors.amount = `That's more than your available balance of ${exactMoney(availableBalance)}.`
  }
  if (!values.purpose) {
    errors.purpose = 'Choose what this payment is for.'
  }
  if (values.note.length > 140) {
    errors.note = 'Keep the note under 140 characters.'
  }
  return errors
}

function toValues(draft?: PaymentDraft): FormValues {
  return {
    recipientAccount: draft?.recipientAccount ?? '',
    amount: draft ? String(draft.amount) : '',
    purpose: draft?.purpose ?? '',
    note: draft?.note ?? '',
  }
}

export function PaymentDetailsForm({
  initial,
  availableBalance,
  onContinue,
}: {
  initial?: PaymentDraft
  availableBalance: string
  onContinue: (draft: PaymentDraft) => void
}) {
  const [values, setValues] = useState<FormValues>(() => toValues(initial))
  const [touched, setTouched] = useState<Partial<Record<keyof FormValues, boolean>>>({})
  const [submitted, setSubmitted] = useState(false)
  const errors = validate(values, availableBalance)
  const show = (key: keyof FormValues) => (submitted || touched[key]) && errors[key]

  function update<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  function blur(key: keyof FormValues) {
    setTouched((prev) => ({ ...prev, [key]: true }))
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitted(true)
    if (Object.keys(errors).length > 0) {
      const firstInvalid = event.currentTarget.querySelector<HTMLElement>('[aria-invalid="true"]')
      firstInvalid?.focus()
      return
    }
    onContinue({
      recipientAccount: values.recipientAccount.trim().replace(/\s/g, ''),
      amount: values.amount.trim(),
      purpose: values.purpose as PaymentPurpose,
      note: values.note.trim() || undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Card>
        <CardHeader>
          <CardTitle>Who are you paying?</CardTitle>
          <CardDescription>{"You'll be able to review everything before any money is sent."}</CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup>
            <Field data-invalid={show('recipientAccount') ? true : undefined}>
              <FieldLabel htmlFor="recipientAccount">LedgerChain account number</FieldLabel>
              <Input
                id="recipientAccount"
                inputMode="text"
                autoCapitalize="none"
                spellCheck={false}
                placeholder="001234567890"
                value={values.recipientAccount}
                onChange={(e) => update('recipientAccount', e.target.value)}
                onBlur={() => blur('recipientAccount')}
                aria-invalid={show('recipientAccount') ? true : undefined}
                aria-describedby={show('recipientAccount') ? 'recipientAccount-error' : 'recipientAccount-hint'}
              />
              {show('recipientAccount') ? (
                <FieldError id="recipientAccount-error">{errors.recipientAccount}</FieldError>
              ) : (
                <FieldDescription id="recipientAccount-hint">
                  {"We'll check this account exists before sending."}
                </FieldDescription>
              )}
            </Field>

            <Field data-invalid={show('amount') ? true : undefined}>
              <FieldLabel htmlFor="amount">Amount</FieldLabel>
              <InputGroup>
                <InputGroupAddon>
                  <InputGroupText>₹</InputGroupText>
                </InputGroupAddon>
                <InputGroupInput
                  id="amount"
                  inputMode="decimal"
                  placeholder="0"
                  className="tabular-nums"
                  value={values.amount}
                  onChange={(e) => update('amount', e.target.value.replace(/[^\d.]/g, ''))}
                  onBlur={() => blur('amount')}
                  aria-invalid={show('amount') ? true : undefined}
                  aria-describedby={show('amount') ? 'amount-error' : 'amount-hint'}
                />
              </InputGroup>
              {show('amount') ? (
                <FieldError id="amount-error">{errors.amount}</FieldError>
              ) : (
                <FieldDescription id="amount-hint">
                  Available balance: <span className="font-medium text-foreground">{exactMoney(availableBalance)}</span>
                </FieldDescription>
              )}
            </Field>

            <Field data-invalid={show('purpose') ? true : undefined}>
              <FieldLabel htmlFor="purpose">What is this payment for?</FieldLabel>
              <Select
                items={purposeItems}
                value={values.purpose || null}
                onValueChange={(value) => {
                  update('purpose', (value ?? '') as PaymentPurpose | '')
                  blur('purpose')
                }}
              >
                <SelectTrigger
                  id="purpose"
                  className="w-full"
                  aria-invalid={show('purpose') ? true : undefined}
                  aria-describedby={show('purpose') ? 'purpose-error' : undefined}
                >
                  <SelectValue placeholder="Choose a purpose" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {purposeItems.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              {show('purpose') && <FieldError id="purpose-error">{errors.purpose}</FieldError>}
            </Field>

            <Field data-invalid={show('note') ? true : undefined}>
              <FieldLabel htmlFor="note">
                Note <span className="font-normal text-muted-foreground">(optional)</span>
              </FieldLabel>
              <Textarea
                id="note"
                rows={2}
                placeholder="e.g. Invoice #2291 for September"
                value={values.note}
                onChange={(e) => update('note', e.target.value)}
                onBlur={() => blur('note')}
                aria-invalid={show('note') ? true : undefined}
                aria-describedby="note-hint"
              />
              {show('note') ? (
                <FieldError>{errors.note}</FieldError>
              ) : (
                <FieldDescription id="note-hint">The recipient will see this note.</FieldDescription>
              )}
            </Field>
          </FieldGroup>
        </CardContent>
        <CardFooter className="justify-end">
          <Button type="submit" size="lg">
            Review payment
            <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
          </Button>
        </CardFooter>
      </Card>
    </form>
  )
}
