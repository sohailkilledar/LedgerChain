'use client'

import { ArrowLeftIcon, InfoIcon, LockIcon } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { purposeLabels } from '@/lib/ledger/format'
import { exactBalanceAfter, exactMoney } from '@/lib/ledger/api-client'
import type { PaymentDraft } from '@/lib/ledger/types'

export function PaymentReview({
  draft,
  availableBalance,
  onBack,
  onConfirm,
}: {
  draft: PaymentDraft
  availableBalance: string
  onBack: () => void
  onConfirm: () => void
}) {
  const rows = [
    { label: 'Recipient account', value: draft.recipientAccount, mono: true },
    { label: 'Purpose', value: purposeLabels[draft.purpose] },
    ...(draft.note ? [{ label: 'Note', value: draft.note }] : []),
    { label: 'Fee', value: 'No fee' },
    { label: 'Balance after', value: exactMoney(exactBalanceAfter(availableBalance, draft.amount)) },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Review your payment</CardTitle>
        <CardDescription>Check the details carefully. You can go back to make changes.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-1 rounded-xl bg-muted/60 px-4 py-6 text-center">
          <span className="text-sm text-muted-foreground">You are sending</span>
          <span className="text-4xl font-semibold tabular-nums tracking-tight">{exactMoney(draft.amount)}</span>
          <span className="text-sm text-muted-foreground">to account {draft.recipientAccount}</span>
        </div>

        <dl className="flex flex-col">
          {rows.map((row, index) => (
            <div key={row.label}>
              {index > 0 && <Separator />}
              <div className="flex items-start justify-between gap-6 py-3">
                <dt className="text-sm text-muted-foreground">{row.label}</dt>
                <dd className={row.mono ? 'text-right font-mono text-[0.8125rem] break-all' : 'text-right text-sm font-medium'}>
                  {row.value}
                </dd>
              </div>
            </div>
          ))}
        </dl>

        <Alert>
          <InfoIcon aria-hidden="true" />
          <AlertTitle>Payments are permanent once confirmed</AlertTitle>
          <AlertDescription>
            {"After you confirm, this payment is recorded on a secure ledger and can't be reversed. If something looks wrong, go back and fix it now."}
          </AlertDescription>
        </Alert>
      </CardContent>
      <CardFooter className="flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button type="button" variant="outline" size="lg" onClick={onBack} className="w-full sm:w-auto">
          <ArrowLeftIcon data-icon="inline-start" aria-hidden="true" />
          Edit details
        </Button>
        <Button type="button" size="lg" onClick={onConfirm} className="w-full sm:w-auto">
          <LockIcon data-icon="inline-start" aria-hidden="true" />
          Confirm and send {exactMoney(draft.amount)}
        </Button>
      </CardFooter>
    </Card>
  )
}
