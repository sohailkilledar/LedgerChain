'use client'

import { useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  ArrowDownToLineIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  CheckCircle2Icon,
  LandmarkIcon,
  LoaderCircleIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { exactMoney, requestJson } from '@/lib/ledger/api-client'

type DemoFundingResponse = {
  id: string
  reference: string
  amount: string
  balance: string
  currency: 'INR'
  demo: true
  created_at: string
}

type Step = 'amount' | 'approval' | 'complete'
const presets = ['500', '1000', '2500', '5000']
const maxDemoAmount = 1_000_000

function validAmount(value: string) {
  if (!/^\d+(?:\.\d{1,2})?$/.test(value)) return false
  const amount = Number(value)
  return Number.isFinite(amount) && amount > 0 && amount <= maxDemoAmount
}

export function AddFundsDialog() {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<Step>('amount')
  const [amount, setAmount] = useState('1000')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [receipt, setReceipt] = useState<DemoFundingResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const idempotencyKey = useRef<string | null>(null)
  const normalizedAmount = amount
  const amountIsValid = validAmount(normalizedAmount)

  function reset() {
    setStep('amount')
    setAmount('1000')
    setReceipt(null)
    setError(null)
    setIsSubmitting(false)
    idempotencyKey.current = null
  }

  async function approveDemoTransfer() {
    setError(null)
    setIsSubmitting(true)
    idempotencyKey.current ??= crypto.randomUUID()
    try {
      const result = await requestJson<DemoFundingResponse>('/demo-fundings/demo', {
        method: 'POST',
        body: JSON.stringify({ amount: normalizedAmount }),
        idempotencyKey: idempotencyKey.current,
      })
      setReceipt(result)
      setStep('complete')
      router.refresh()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'The demo request could not be completed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <Button variant="outline" size="lg" onClick={() => { reset(); setOpen(true) }}>
        <ArrowDownToLineIcon data-icon="inline-start" aria-hidden="true" />
        Add demo funds
      </Button>
      <Dialog
        open={open}
        onOpenChange={(nextOpen) => {
          if (!nextOpen && isSubmitting) return
          setOpen(nextOpen)
          if (!nextOpen) reset()
        }}
      >
        <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-md">
          {step === 'amount' && (
            <>
              <DialogHeader>
                <Badge variant="secondary" className="w-fit gap-1.5">
                  <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
                  Demo funding
                </Badge>
                <DialogTitle className="pt-1">Add simulated funds</DialogTitle>
                <DialogDescription>
                  Choose an amount, then review the simulated bank approval before funds are added to your demo balance.
                </DialogDescription>
              </DialogHeader>

              <div className="flex items-center gap-3 rounded-xl border bg-muted/30 p-3.5">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <LandmarkIcon className="size-5" aria-hidden="true" />
                </span>
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="text-sm font-medium">LedgerChain Demo Bank</span>
                  <span className="text-xs text-muted-foreground">Everyday checking ···· 4821</span>
                </div>
                <Badge variant="outline">Sandbox</Badge>
              </div>

              <FieldGroup className="gap-3">
                <Field>
                  <FieldLabel htmlFor="demo-funding-amount">Amount to add</FieldLabel>
                  <div className="relative">
                    <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-muted-foreground" aria-hidden="true">
                      ₹
                    </span>
                    <Input
                      id="demo-funding-amount"
                      type="text"
                      inputMode="decimal"
                      autoComplete="off"
                      value={amount}
                      onChange={(event) => {
                        setAmount(event.target.value)
                        setError(null)
                        idempotencyKey.current = null
                      }}
                      aria-invalid={amount.length > 0 && !amountIsValid}
                      className="pl-8 text-lg tabular-nums"
                    />
                  </div>
                  <FieldDescription>Up to ₹10,00,000 per demo request. INR only.</FieldDescription>
                </Field>
                <div className="flex flex-wrap gap-2" aria-label="Suggested amounts">
                  {presets.map((preset) => (
                    <Button
                      key={preset}
                      type="button"
                      size="sm"
                      variant=                      {normalizedAmount === preset ? 'secondary' : 'outline'}

                      onClick={() => {
                        setAmount(preset)
                        setError(null)
                        idempotencyKey.current = null
                      }}
                    >
                      {exactMoney(preset)}
                    </Button>
                  ))}
                </div>
              </FieldGroup>

              <Alert>
                <ShieldCheckIcon aria-hidden="true" />
                <AlertDescription>
                  Demo only. No real bank is contacted and no real money moves.
                </AlertDescription>
              </Alert>

              <DialogFooter>
                <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button disabled={!amountIsValid} onClick={() => { setError(null); setStep('approval') }}>
                  Continue to approval
                  <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
                </Button>
              </DialogFooter>
            </>
          )}

          {step === 'approval' && (
            <>
              <DialogHeader>
                <Badge variant="secondary" className="w-fit gap-1.5">Bank approval · demo</Badge>
                <DialogTitle className="pt-1">Review your transfer</DialogTitle>
                <DialogDescription>
                  This is a simulated approval screen. Nothing is sent to a bank.
                </DialogDescription>
              </DialogHeader>

              <div className="rounded-xl border bg-muted/20 p-4">
                <div className="flex items-center justify-between gap-3 border-b pb-3">
                  <span className="text-sm text-muted-foreground">From</span>
                  <span className="text-right text-sm font-medium">LedgerChain Demo Bank<br /><span className="font-normal text-muted-foreground">Checking ···· 4821</span></span>
                </div>
                <div className="flex items-center justify-between gap-3 border-b py-3">
                  <span className="text-sm text-muted-foreground">To</span>
                  <span className="text-sm font-medium">Your LedgerChain account</span>
                </div>
                <div className="flex items-baseline justify-between gap-3 pt-3">
                  <span className="text-sm text-muted-foreground">Amount</span>
                  <span className="text-2xl font-semibold tracking-tight tabular-nums">{exactMoney(normalizedAmount)}</span>
                </div>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <DialogFooter className="sm:justify-between">
                <Button variant="ghost" disabled={isSubmitting} onClick={() => { setStep('amount'); setError(null) }}>
                  <ArrowLeftIcon data-icon="inline-start" aria-hidden="true" />
                  Back
                </Button>
                <Button disabled={isSubmitting} onClick={approveDemoTransfer}>
                  {isSubmitting ? <LoaderCircleIcon data-icon="inline-start" className="animate-spin" aria-hidden="true" /> : <ShieldCheckIcon data-icon="inline-start" aria-hidden="true" />}
                  {isSubmitting ? 'Processing demo request' : 'Approve demo transfer'}
                </Button>
              </DialogFooter>
            </>
          )}

          {step === 'complete' && receipt && (
            <>
              <DialogHeader>
                <span className="flex size-12 items-center justify-center rounded-full bg-success/10 text-success">
                  <CheckCircle2Icon className="size-6" aria-hidden="true" />
                </span>
                <DialogTitle className="pt-1">Demo funds added</DialogTitle>
                <DialogDescription>
                  Your simulated bank transfer is approved. Your LedgerChain demo balance has been updated.
                </DialogDescription>
              </DialogHeader>

              <div className="rounded-xl border bg-muted/20 p-4">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-sm text-muted-foreground">Added</span>
                  <span className="text-xl font-semibold tabular-nums">{exactMoney(receipt.amount)}</span>
                </div>
                <div className="mt-3 flex items-baseline justify-between gap-3 border-t pt-3">
                  <span className="text-sm text-muted-foreground">Updated balance</span>
                  <span className="text-sm font-semibold tabular-nums">{exactMoney(receipt.balance)}</span>
                </div>
                <p className="mt-3 break-all border-t pt-3 font-mono text-xs text-muted-foreground">Ref: {receipt.reference}</p>
              </div>
              <Alert>
                <ShieldCheckIcon aria-hidden="true" />
                <AlertDescription>This is a demo balance update. No real money moved.</AlertDescription>
              </Alert>
              <DialogFooter>
                <Button className="w-full" onClick={() => { setOpen(false); reset() }}>Done</Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
