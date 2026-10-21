'use client'

import { ChevronDownIcon, CircleCheckIcon, CircleXIcon, ListIcon, PencilIcon, RotateCcwIcon, SendIcon, ShieldCheckIcon } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { CopyButton } from '@/components/ledger/copy-button'
import { RecordDisclosure } from '@/components/ledger/record-disclosure'
import type { ActivityRecord, LedgerErrorShape } from '@/lib/ledger/types'
import { cn } from '@/lib/utils'

export function PaymentSuccess({ record, onNew }: { record: ActivityRecord; onNew: () => void }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-center gap-3 rounded-xl border border-success/30 bg-success-soft px-5 py-8 text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-success text-success-foreground">
          <CircleCheckIcon className="size-6" aria-hidden="true" />
        </span>
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold tracking-tight">
            {record.status === 'completed' ? 'Payment recorded' : 'Payment processing'}
          </h2>
          <p className="max-w-sm text-sm text-pretty text-muted-foreground">
            {record.status === 'completed'
              ? 'The backend recorded this payment. Blockchain anchoring is separate and is not implied.'
              : 'The backend accepted this payment, but it has not yet reported completion. Check the reference below for updates.'}
          </p>
        </div>
      </div>
      <RecordDisclosure record={record} />
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="outline" size="lg" render={<Link href="/activity" />} nativeButton={false}>
          <ListIcon data-icon="inline-start" aria-hidden="true" />
          Go to activity
        </Button>
        <Button size="lg" onClick={onNew}>
          <SendIcon data-icon="inline-start" aria-hidden="true" />
          Send another payment
        </Button>
      </div>
    </div>
  )
}

export function PaymentFailure({
  error,
  onRetry,
  onEdit,
}: {
  error: LedgerErrorShape
  onRetry: () => void
  onEdit: () => void
}) {
  const [showTechnical, setShowTechnical] = useState(false)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start gap-4">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-destructive-soft text-destructive">
            <CircleXIcon className="size-5" aria-hidden="true" />
          </span>
          <div className="flex flex-col gap-1">
            <CardTitle>
              <h2 className="text-base font-semibold">Payment didn&apos;t go through</h2>
            </CardTitle>
            <CardDescription className="text-pretty">{error.message}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {error.outcomeUnknown ? (
          <Alert>
            <ShieldCheckIcon aria-hidden="true" />
            <AlertTitle>Payment status is unknown</AlertTitle>
            <AlertDescription>
              The request may have reached the backend. Do not start a new payment; retrying here uses the same idempotency key to prevent a duplicate.
            </AlertDescription>
          </Alert>
        ) : !error.committed ? (
          <Alert className="border-success/30 bg-success-soft">
            <ShieldCheckIcon aria-hidden="true" className="text-success" />
            <AlertTitle>Your money is safe</AlertTitle>
            <AlertDescription>No money left your account and nothing was recorded on the ledger.</AlertDescription>
          </Alert>
        ) : null}

        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-medium">What you can do</h3>
          <ul className="flex list-disc flex-col gap-1 pl-5 text-sm text-muted-foreground">
            <li>Double-check the recipient&apos;s LedgerChain account number.</li>
            <li>Ask the recipient to confirm their account is active.</li>
            {error.retryable && <li>Retry this request here to reuse its idempotency key; do not start a separate payment while the outcome is uncertain.</li>}
          </ul>
        </div>

        {error.technicalMessage && (
          <Collapsible open={showTechnical} onOpenChange={setShowTechnical}>
            <div className="rounded-lg border bg-muted/40">
              <CollapsibleTrigger
                render={
                  <Button
                    variant="ghost"
                    className="h-10 w-full justify-between rounded-lg px-3 text-muted-foreground hover:text-foreground"
                  />
                }
              >
                {showTechnical ? 'Hide technical details' : 'View technical details'}
                <ChevronDownIcon
                  data-icon="inline-end"
                  aria-hidden="true"
                  className={cn('transition-transform', showTechnical && 'rotate-180')}
                />
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="flex flex-col gap-3 border-t px-3 py-4">
                  <p className="text-xs text-muted-foreground">
                    Share these details with support if the problem continues.
                  </p>
                  <dl className="flex flex-col gap-2 text-xs">
                    <div className="flex items-center justify-between gap-4">
                      <dt className="text-muted-foreground">Error code</dt>
                      <dd className="flex items-center gap-1 font-mono">
                        {error.code}
                        <CopyButton value={error.code} label="error code" />
                      </dd>
                    </div>
                    <div className="flex flex-col gap-1">
                      <dt className="text-muted-foreground">Ledger response</dt>
                      <dd className="rounded-md bg-card p-2 font-mono break-all">{error.technicalMessage}</dd>
                    </div>
                  </dl>
                </div>
              </CollapsibleContent>
            </div>
          </Collapsible>
        )}
      </CardContent>
      <CardFooter className="flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="outline" size="lg" onClick={onEdit} className="w-full sm:w-auto">
          <PencilIcon data-icon="inline-start" aria-hidden="true" />
          Edit details
        </Button>
        {error.retryable && (
          <Button size="lg" onClick={onRetry} className="w-full sm:w-auto">
            <RotateCcwIcon data-icon="inline-start" aria-hidden="true" />
            Try again
          </Button>
        )}
      </CardFooter>
    </Card>
  )
}
