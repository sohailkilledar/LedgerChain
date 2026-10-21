'use client'

import { useMemo, useRef, useState, type FormEvent } from 'react'
import { ArrowUpRightIcon, CheckIcon, CircleAlertIcon, Clock3Icon, PlusIcon, SendIcon, XIcon } from 'lucide-react'
import Link from 'next/link'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ledgerService, newIdempotencyKey } from '@/lib/ledger/service'
import { exactMoney, type BackendFinanceBudget, type BackendPaymentRequest, type BackendPaymentRequestEvent, type BackendOrganization } from '@/lib/ledger/api-client'
import { LedgerError } from '@/lib/ledger/types'

const money = (value: string) => exactMoney(value)
const dateLabel = (value: string) => new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(value))

export function FinanceWorkspace({
  account: initialAccount,
  initialBudgets,
  initialRequests,
}: {
  account: BackendOrganization
  initialBudgets: BackendFinanceBudget[]
  initialRequests: BackendPaymentRequest[]
}) {
  const [account, setAccount] = useState(initialAccount)
  const [budgets, setBudgets] = useState(() => initialBudgets.filter((budget) => budget.organization_id === initialAccount.id))
  const [requests, setRequests] = useState(() => initialRequests.filter((request) => request.organization_id === initialAccount.id))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const requestKey = useRef<string | undefined>(undefined)
  const pending = useMemo(() => requests.filter((request) => request.status === 'SUBMITTED').length, [requests])
  const canApprove = account.role === 'owner'

  async function refresh() {
    const [nextAccount, nextBudgets, nextRequests] = await Promise.all([
      ledgerService.getAccount(),
      ledgerService.listFinanceBudgets(),
      ledgerService.listPaymentRequests(),
    ])
    setAccount(nextAccount)
    setBudgets(nextBudgets.filter((budget) => budget.organization_id === nextAccount.id))
    setRequests(nextRequests.filter((request) => request.organization_id === nextAccount.id))
  }

  async function run(action: () => Promise<unknown>) {
    setBusy(true)
    setError(null)
    try {
      await action()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The finance action could not be completed.')
      try {
        await refresh()
      } catch {
        // Preserve the action error if the read refresh also fails.
      }
      setBusy(false)
      return
    }
    try {
      await refresh()
    } catch {
      setError('The finance action was saved, but the latest data could not be loaded. Refresh this page to confirm the current state.')
    } finally {
      setBusy(false)
    }
  }

  async function createRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const idempotencyKey = requestKey.current ?? newIdempotencyKey()
    requestKey.current = idempotencyKey
    await run(async () => {
      let created: BackendPaymentRequest
      try {
        created = await ledgerService.createPaymentRequest({
          organization_id: account.id,
          recipient_account: String(form.get('recipient_account') ?? ''),
          amount: String(form.get('amount') ?? ''),
          purpose: String(form.get('purpose') ?? 'other') as BackendPaymentRequest['purpose'],
          note: String(form.get('note') ?? '').trim() || undefined,
          budget_id: String(form.get('budget_id') ?? '') || undefined,
        }, idempotencyKey)
      } catch (cause) {
        if (!(cause instanceof LedgerError) || !cause.outcomeUnknown) requestKey.current = undefined
        throw cause
      }
      try {
        await ledgerService.submitPaymentRequest(created.id)
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'The request was saved but could not be submitted. Retry to continue.')
        throw cause
      }
      requestKey.current = undefined
      formElement.reset()
    })
  }

  async function createBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    await run(async () => {
      await ledgerService.createFinanceBudget({
        organization_id: account.id,
        name: String(form.get('name') ?? ''),
        category: String(form.get('category') ?? '').trim() || undefined,
        allocated_amount: String(form.get('allocated_amount') ?? ''),
        period_start: String(form.get('period_start') ?? ''),
        period_end: String(form.get('period_end') ?? ''),
      })
      formElement.reset()
    })
  }

  return (
    <div className="flex flex-col gap-6">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <section aria-label="Payment request workflow" className="rounded-xl border bg-card p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h2 className="font-semibold">Payment request lifecycle</h2>
            <p className="text-sm text-muted-foreground">Approval reserves budget; execution posts through the existing payment and double-entry ledger services.</p>
          </div>
          <Badge variant="outline">{pending} awaiting review</Badge>
        </div>
        <ol className="mt-5 grid gap-2 sm:grid-cols-5">
          {['Draft', 'Submit', 'Approve', 'Budget check', 'Payment + ledger'].map((step, index) => (
            <li key={step} className="flex items-center gap-2 rounded-md bg-muted/50 p-3 text-sm">
              <span className="flex size-6 shrink-0 items-center justify-center rounded-full border bg-background text-xs font-semibold">{index + 1}</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex flex-col gap-5">
          <Card>
            <CardHeader>
              <CardTitle>Payment requests</CardTitle>
              <CardDescription>Organization members can view requests. Owners review them; only a completed request creates a payment and ledger entry.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {requests.length === 0 ? (
                <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">No payment requests have been recorded for this organization.</p>
              ) : requests.map((request) => (
                <article key={request.id} className="rounded-lg border p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-medium">{request.recipient_name}</h3>
                        <Badge variant={request.status === 'REJECTED' ? 'destructive' : request.status === 'COMPLETED' ? 'default' : 'secondary'}>{request.status.replaceAll('_', ' ')}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{money(request.amount)} · {request.purpose} · {dateLabel(request.created_at)}</p>
                      <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{request.recipient_account}</p>
                      {request.note && <p className="mt-2 text-sm">{request.note}</p>}
                      {request.approver_user_id && <p className="mt-2 text-xs text-muted-foreground">Decision by {request.approver_user_id}{request.approved_at ? ` · ${dateLabel(request.approved_at)}` : ''}{request.approval_note ? ` · ${request.approval_note}` : ''}</p>}
                      {request.payment_reference && <p className="mt-2 text-xs text-muted-foreground">Payment {request.payment_reference} · ledger posted by payment service</p>}
                    </div>
                    {canApprove && <div className="flex flex-wrap gap-2">
                      {request.status === 'SUBMITTED' && <>
                        <Button size="sm" disabled={busy} onClick={() => void run(() => ledgerService.decidePaymentRequest(request.id, 'approve'))}><CheckIcon data-icon="inline-start" aria-hidden="true" />Approve</Button>
                        <Button size="sm" variant="outline" disabled={busy} onClick={() => {
                          const note = window.prompt('Reason for rejecting this payment request')?.trim()
                          if (note) void run(() => ledgerService.decidePaymentRequest(request.id, 'reject', note))
                        }}><XIcon data-icon="inline-start" aria-hidden="true" />Reject</Button>
                      </>}
                      {request.status === 'APPROVED' && <Button size="sm" disabled={busy} onClick={() => void run(() => ledgerService.executePaymentRequest(request.id))}><SendIcon data-icon="inline-start" aria-hidden="true" />Execute payment</Button>}
                    </div>}
                  </div>
                  <RequestProgress status={request.status} />
                  <RequestHistory requestId={request.id} />
                </article>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>New payment request</CardTitle>
              <CardDescription>Creates an internal INR transfer request. It will not move funds until an owner approves and executes it.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={createRequest} className="flex flex-col gap-4">
                <FieldGroup>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field>
                      <FieldLabel htmlFor="request-recipient">Recipient account number</FieldLabel>
                      <Input id="request-recipient" name="recipient_account" required inputMode="numeric" minLength={9} maxLength={18} />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="request-amount">Amount (INR)</FieldLabel>
                      <Input id="request-amount" name="amount" required inputMode="decimal" pattern="[0-9]+(\.[0-9]{1,2})?" />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="request-purpose">Purpose</FieldLabel>
                      <select id="request-purpose" name="purpose" defaultValue="supplier" className="h-10 rounded-lg border border-input bg-background px-3 text-sm">
                        <option value="supplier">Supplier</option><option value="invoice">Invoice</option><option value="salary">Salary</option><option value="personal">Personal</option><option value="other">Other</option>
                      </select>
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="request-budget">Budget (optional)</FieldLabel>
                      <select id="request-budget" name="budget_id" defaultValue="" className="h-10 rounded-lg border border-input bg-background px-3 text-sm">
                        <option value="">No linked budget</option>
                        {budgets.filter((budget) => budget.status === 'active').map((budget) => <option key={budget.id} value={budget.id}>{budget.name} · {money(budget.remaining_amount)} remaining</option>)}
                      </select>
                    </Field>
                  </div>
                  <Field>
                    <FieldLabel htmlFor="request-note">Business note</FieldLabel>
                    <Textarea id="request-note" name="note" rows={2} maxLength={140} />
                  </Field>
                </FieldGroup>
                <div className="flex justify-end"><Button disabled={busy} type="submit"><PlusIcon data-icon="inline-start" aria-hidden="true" />Create and submit</Button></div>
              </form>
            </CardContent>
          </Card>
        </div>

        <aside className="flex flex-col gap-5">
          {canApprove && <Card>
            <CardHeader>
              <CardTitle>Create a budget</CardTitle>
              <CardDescription>Usage counts committed approvals and completed payment requests linked to this budget.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={createBudget} className="flex flex-col gap-4">
                <FieldGroup>
                  <Field><FieldLabel htmlFor="budget-name">Name</FieldLabel><Input id="budget-name" name="name" required maxLength={120} /></Field>
                  <Field><FieldLabel htmlFor="budget-category">Category (optional)</FieldLabel><Input id="budget-category" name="category" maxLength={80} /></Field>
                  <Field><FieldLabel htmlFor="budget-allocation">Allocation (INR)</FieldLabel><Input id="budget-allocation" name="allocated_amount" required inputMode="decimal" pattern="[0-9]+(\.[0-9]{1,2})?" /></Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field><FieldLabel htmlFor="budget-start">Starts</FieldLabel><Input id="budget-start" name="period_start" type="date" required /></Field>
                    <Field><FieldLabel htmlFor="budget-end">Ends</FieldLabel><Input id="budget-end" name="period_end" type="date" required /></Field>
                  </div>
                </FieldGroup>
                <Button disabled={busy} type="submit"><PlusIcon data-icon="inline-start" aria-hidden="true" />Create budget</Button>
              </form>
            </CardContent>
          </Card>}

          <Card>
            <CardHeader><CardTitle>Budget utilization</CardTitle><CardDescription>Values are computed from real requests linked to each budget.</CardDescription></CardHeader>
            <CardContent className="flex flex-col gap-5">
              {budgets.length === 0 ? <p className="text-sm text-muted-foreground">No budgets have been configured.</p> : budgets.map((budget) => {
                const percent = Math.min(100, Math.max(0, Number(budget.utilization_percent)))
                return <div key={budget.id} className="flex flex-col gap-2">
                  <div className="flex items-start justify-between gap-3">
                    <div><p className="font-medium">{budget.name}</p><p className="text-xs text-muted-foreground">{budget.category || 'Uncategorized'} · {dateLabel(budget.period_start)} – {dateLabel(budget.period_end)}</p></div>
                    <Badge variant="outline">{budget.status}</Badge>
                  </div>
                  <div aria-label={`${budget.name}, ${budget.utilization_percent}% utilized`} role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} /></div>
                  <dl className="grid grid-cols-2 gap-2 text-xs">
                    <div><dt className="text-muted-foreground">Allocated</dt><dd className="font-medium">{money(budget.allocated_amount)}</dd></div>
                    <div><dt className="text-muted-foreground">Remaining</dt><dd className="font-medium">{money(budget.remaining_amount)}</dd></div>
                    <div><dt className="text-muted-foreground">Spent</dt><dd className="font-medium">{money(budget.spent_amount)}</dd></div>
                    <div><dt className="text-muted-foreground">Committed</dt><dd className="font-medium">{money(budget.committed_amount)}</dd></div>
                  </dl>
                  <p className="text-[11px] text-muted-foreground">{budget.utilization_percent}% utilized</p>
                </div>
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Available balance</CardTitle><CardDescription>Transfers use the current internal payment engine.</CardDescription></CardHeader>
            <CardContent className="flex flex-col gap-3">
              <p className="text-2xl font-semibold tabular-nums">{money(account.balance)}</p>
              <Button variant="outline" render={<Link href="/payments/new" />} nativeButton={false}>Open payments <ArrowUpRightIcon data-icon="inline-end" aria-hidden="true" /></Button>
              <p className="text-xs text-muted-foreground">No external bank is contacted. Demo funding remains test-only.</p>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  )
}

function RequestProgress({ status }: { status: BackendPaymentRequest['status'] }) {
  const order: BackendPaymentRequest['status'][] = ['DRAFT', 'SUBMITTED', 'APPROVED', 'PAYMENT_CREATED', 'COMPLETED']
  const current = status === 'REJECTED' ? 1 : order.indexOf(status)
  return (
    <ol aria-label="Request progress" className="mt-4 flex flex-wrap gap-2">
      {order.map((step, index) => (
        <li key={step} className={`flex items-center gap-1.5 rounded-full px-2 py-1 text-[11px] ${index <= current && status !== 'REJECTED' ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'}`}>
          {index < current && status !== 'REJECTED' ? <CheckIcon aria-hidden="true" className="size-3" /> : index === current ? <Clock3Icon aria-hidden="true" className="size-3" /> : null}
          {step.replaceAll('_', ' ').toLowerCase()}
        </li>
      ))}
      {status === 'REJECTED' && <li className="flex items-center gap-1.5 rounded-full bg-destructive/10 px-2 py-1 text-[11px] text-destructive"><CircleAlertIcon className="size-3" aria-hidden="true" />Rejected</li>}
    </ol>
  )
}

function RequestHistory({ requestId }: { requestId: string }) {
  const [events, setEvents] = useState<BackendPaymentRequestEvent[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  async function load() {
    if (events || loading) return
    setLoading(true)
    try {
      setEvents(await ledgerService.getPaymentRequestHistory(requestId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'History could not be loaded.')
    } finally {
      setLoading(false)
    }
  }
  return (
    <div className="mt-3 border-t pt-3">
      <Button type="button" variant="ghost" size="sm" onClick={() => void load()} disabled={loading}>
        {loading ? 'Loading history…' : events ? 'History loaded' : 'View transition history'}
      </Button>
      {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
      {events && <ol className="mt-2 flex flex-col gap-2">
        {events.map((event) => <li key={event.id} className="flex items-start gap-2 text-xs"><span className="mt-1 size-1.5 shrink-0 rounded-full bg-primary" /><span><strong>{event.from_status ? `${event.from_status} → ` : ''}{event.to_status}</strong>{event.detail ? ` · ${event.detail}` : ''}<span className="block text-muted-foreground">{dateLabel(event.created_at)} · actor {event.actor_user_id}</span></span></li>)}
      </ol>}
    </div>
  )
}
