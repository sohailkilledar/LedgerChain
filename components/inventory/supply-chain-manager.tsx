'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { ledgerService, newIdempotencyKey } from '@/lib/ledger/service'
import type { BackendBlockchainRecord, BackendBlockchainStatus, BackendInventoryBatch, BackendInventoryShipment, BackendProduct, BackendShipmentEventVerification } from '@/lib/ledger/api-client'

const stages = ['PREPARED', 'DISPATCHED', 'IN_TRANSIT', 'RECEIVED'] as const
const stageLabels: Record<(typeof stages)[number], string> = {
  PREPARED: 'Prepared',
  DISPATCHED: 'Dispatched',
  IN_TRANSIT: 'In transit',
  RECEIVED: 'Received',
}

function formattedQuantity(value: string, unit: string | null) {
  const amount = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 3 }).format(Number(value))
  return unit ? `${amount} ${unit}` : amount
}

function ShipmentProgress({ status }: { status: BackendInventoryShipment['status'] }) {
  const current = stages.indexOf(status as (typeof stages)[number])
  if (status === 'REJECTED') {
    return <Badge variant="destructive">Rejected</Badge>
  }
  return (
    <ol aria-label={`Shipment status: ${stageLabels[status as (typeof stages)[number]]}`} className="flex flex-wrap items-center gap-2 text-xs">
      {stages.map((stage, index) => {
        const complete = current >= index
        return (
          <li key={stage} className="flex items-center gap-2">
            <span className={`flex items-center gap-1.5 ${complete ? 'text-foreground' : 'text-muted-foreground'}`}>
              <span aria-hidden="true" className={`size-2 rounded-full ${complete ? 'bg-primary' : 'bg-muted-foreground/30'}`} />
              {stageLabels[stage]}
            </span>
            {index < stages.length - 1 && <span aria-hidden="true" className="text-muted-foreground/60">·</span>}
          </li>
        )
      })}
    </ol>
  )
}

export function SupplyChainManager({
  initialBatches,
  initialShipments,
  products,
  organizationId,
  organizationName,
  organizationAccountNumber,
  organizationRole,
  blockchainStatus,
  initialHasMoreShipments,
}: {
  initialBatches: BackendInventoryBatch[]
  initialShipments: BackendInventoryShipment[]
  products: BackendProduct[]
  organizationId: string
  organizationName: string
  organizationAccountNumber: string
  organizationRole: string
  blockchainStatus: BackendBlockchainStatus
  initialHasMoreShipments: boolean
}) {
  const router = useRouter()
  const [batches, setBatches] = useState(initialBatches)
  const [shipments, setShipments] = useState(initialShipments)
  const [hasMoreShipments, setHasMoreShipments] = useState(initialHasMoreShipments)
  const [pending, setPending] = useState(false)
  const [pendingAction, setPendingAction] = useState<string>()
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string>()
  const [notice, setNotice] = useState<string>()
  const [anchorPendingEventId, setAnchorPendingEventId] = useState<string>()
  const [verificationPendingEventId, setVerificationPendingEventId] = useState<string>()
  const [verificationResults, setVerificationResults] = useState<Record<string, BackendShipmentEventVerification>>({})
  const [selectedBatchProduct, setSelectedBatchProduct] = useState('')
  const [receivingShipmentId, setReceivingShipmentId] = useState<string>()
  const [rejectingShipmentId, setRejectingShipmentId] = useState<string>()
  const requestKeys = useRef(new Map<string, string>())
  const isOwner = organizationRole === 'owner'

  useEffect(() => {
    setBatches(initialBatches)
    setShipments(initialShipments)
    setHasMoreShipments(initialHasMoreShipments)
  }, [initialBatches, initialShipments, initialHasMoreShipments])

  async function createBatch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    setPending(true)
    setError(undefined)
    setNotice(undefined)
    try {
      const batch = await ledgerService.createInventoryBatch({
        product_id: String(form.get('product_id') ?? ''),
        batch_code: String(form.get('batch_code') ?? '').trim(),
        manufactured_on: String(form.get('manufactured_on') ?? '') || undefined,
        expires_on: String(form.get('expires_on') ?? '') || undefined,
        notes: String(form.get('notes') ?? '').trim() || undefined,
      })
      setBatches((current) => [batch, ...current.filter((item) => item.id !== batch.id)])
      formElement.reset()
      router.refresh()
      setNotice(`Batch ${batch.batch_code} was created. Stock is only counted after a receipt is recorded.`)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The batch could not be created.')
    } finally {
      setPending(false)
    }
  }

  async function prepareShipment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const batchId = String(form.get('batch_id') ?? '')
    const batch = batches.find((item) => item.id === batchId)
    if (!batch) {
      setError('Choose a valid batch before preparing a shipment.')
      return
    }
    const input = {
      recipient_account_number: String(form.get('recipient_account_number') ?? '').trim(),
      product_id: batch.product_id,
      batch_id: batch.id,
      quantity: String(form.get('quantity') ?? '').trim(),
      source_location: String(form.get('source_location') ?? '').trim(),
      destination_location: String(form.get('destination_location') ?? '').trim(),
      note: String(form.get('note') ?? '').trim() || undefined,
    }
    const keyFingerprint = JSON.stringify(input)
    const key = requestKeys.current.get(keyFingerprint) ?? newIdempotencyKey()
    requestKeys.current.set(keyFingerprint, key)
    setPending(true)
    setError(undefined)
    setNotice(undefined)
    try {
      const shipment = await ledgerService.createInventoryShipment(input, key)
      requestKeys.current.delete(keyFingerprint)
      setShipments((current) => [shipment, ...current.filter((item) => item.id !== shipment.id)])
      formElement.reset()
      setSelectedBatchProduct('')
      setNotice('Shipment prepared. The source quantity will be deducted only when it is dispatched.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The shipment was not confirmed.')
    } finally {
      setPending(false)
    }
  }

  async function transition(shipment: BackendInventoryShipment, action: 'dispatch' | 'transit' | 'receive' | 'reject', input: { destination_location?: string; reason?: string } = {}) {
    const fingerprint = `${shipment.id}:${action}:${JSON.stringify(input)}`
    const key = requestKeys.current.get(fingerprint) ?? newIdempotencyKey()
    requestKeys.current.set(fingerprint, key)
    setPendingAction(fingerprint)
    setError(undefined)
    setNotice(undefined)
    try {
      const updated = await ledgerService.transitionInventoryShipment(shipment.id, action, input, key)
      requestKeys.current.delete(fingerprint)
      setShipments((current) => current.map((item) => item.id === updated.id ? updated : item))
      setReceivingShipmentId(undefined)
      setRejectingShipmentId(undefined)
      setNotice(`Shipment ${updated.id} is now ${updated.status.toLowerCase().replaceAll('_', ' ')}.`)
      router.refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The shipment update was not confirmed.')
    } finally {
      setPendingAction(undefined)
    }
  }

  async function loadMoreShipments() {
    setLoadingMore(true)
    setError(undefined)
    try {
      const page = await ledgerService.listInventoryShipments({ limit: 50, offset: shipments.length })
      setShipments((current) => [...current, ...page.items])
      setHasMoreShipments(page.has_more)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'More shipment history could not be loaded.')
    } finally {
      setLoadingMore(false)
    }
  }

  async function anchorEvidence(shipmentId: string, eventId: string) {
    setAnchorPendingEventId(eventId)
    setError(undefined)
    setNotice(undefined)
    try {
      const record = await ledgerService.anchorShipmentEvent(shipmentId, eventId)
      setShipments((current) => current.map((shipment) => shipment.id !== shipmentId ? shipment : {
        ...shipment,
        events: shipment.events.map((event) => event.id === eventId ? { ...event, blockchain_record: record } : event),
      }))
      setNotice(record.status === 'simulated'
        ? 'Shipment evidence was processed by the development simulator. No public-chain transaction, hash, or block was created.'
        : record.status === 'confirmed'
          ? 'Shipment evidence was confirmed by the configured blockchain provider.'
          : 'Shipment evidence was submitted. Blockchain confirmation is still pending.')
      router.refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Shipment evidence could not be anchored.')
    } finally {
      setAnchorPendingEventId(undefined)
    }
  }

  async function verifyEvidence(shipmentId: string, eventId: string) {
    setVerificationPendingEventId(eventId)
    setError(undefined)
    try {
      const result = await ledgerService.verifyShipmentEvent(shipmentId, eventId)
      setVerificationResults((current) => ({ ...current, [eventId]: result }))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Shipment evidence could not be verified.')
    } finally {
      setVerificationPendingEventId(undefined)
    }
  }

  return (
    <section aria-labelledby="traceability-heading" className="flex flex-col gap-5">
      <div>
        <h2 id="traceability-heading" className="text-xl font-semibold tracking-tight">Batch traceability &amp; shipments</h2>
        <p className="mt-1 text-sm text-muted-foreground">Follow product lots between organizations with backend-recorded, append-only shipment events. No live location tracking is collected.</p>
        <p className="mt-2 text-xs text-muted-foreground">Evidence provider: {blockchainStatus.provider} · {blockchainStatus.health}. {blockchainStatus.provider === 'development' ? 'Development anchors are simulated and never create public-chain transaction data.' : 'Anchors are shown as confirmed only when the configured provider reports a mined confirmation.'}</p>
      </div>

      {error && <Alert variant="destructive"><AlertTitle>Traceability update not confirmed</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      {notice && <Alert><AlertTitle>Traceability updated</AlertTitle><AlertDescription>{notice}</AlertDescription></Alert>}

      <div className="grid gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Create a product batch</CardTitle>
            <CardDescription>Assign a supplier lot code and optional manufacture and expiry dates before receiving stock.</CardDescription>
          </CardHeader>
          <CardContent>
            {isOwner && products.length > 0 ? (
              <form onSubmit={createBatch} className="flex flex-col gap-4">
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor="batch-product">Product</FieldLabel>
                    <select id="batch-product" name="product_id" required className="h-10 rounded-lg border border-input bg-card px-3 text-sm">
                      <option value="">Select product</option>
                      {products.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}
                    </select>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="batch-code">Batch / lot code</FieldLabel>
                    <Input id="batch-code" name="batch_code" required maxLength={80} />
                  </Field>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field><FieldLabel htmlFor="batch-manufactured">Manufactured on</FieldLabel><Input id="batch-manufactured" name="manufactured_on" type="date" /></Field>
                    <Field><FieldLabel htmlFor="batch-expires">Expires on</FieldLabel><Input id="batch-expires" name="expires_on" type="date" /></Field>
                  </div>
                  <Field><FieldLabel htmlFor="batch-notes">Notes (optional)</FieldLabel><Input id="batch-notes" name="notes" maxLength={240} /></Field>
                </FieldGroup>
                <Button type="submit" disabled={pending || products.length === 0}>
                  {pending && <Spinner data-icon="inline-start" />}
                  Create batch
                </Button>
              </form>
            ) : (
              <Alert><AlertTitle>{isOwner ? 'Create a product first' : 'Owner access required'}</AlertTitle><AlertDescription>{isOwner ? 'Add an active product before you create its batch record.' : 'Only an organization owner can create batches and prepare shipments.'}</AlertDescription></Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Prepare a shipment</CardTitle>
            <CardDescription>Choose a recipient by LedgerChain account number. Stock is checked and deducted atomically at dispatch.</CardDescription>
          </CardHeader>
          <CardContent>
            {isOwner && batches.length > 0 ? (
              <form onSubmit={prepareShipment} className="flex flex-col gap-4">
                <FieldGroup>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field><FieldLabel htmlFor="shipment-recipient">Recipient account number</FieldLabel><Input id="shipment-recipient" name="recipient_account_number" inputMode="numeric" pattern="[0-9]{18}" minLength={18} maxLength={18} required /></Field>
                    <Field><FieldLabel htmlFor="shipment-batch">Product batch</FieldLabel><select id="shipment-batch" name="batch_id" value={selectedBatchProduct} onChange={(event) => setSelectedBatchProduct(event.target.value)} required className="h-10 rounded-lg border border-input bg-card px-3 text-sm"><option value="">Select batch</option>{batches.map((batch) => <option key={batch.id} value={batch.id}>{batch.product_name} · {batch.batch_code}</option>)}</select></Field>
                    <Field><FieldLabel htmlFor="shipment-quantity">Quantity</FieldLabel><Input id="shipment-quantity" name="quantity" type="number" min="0.001" step="0.001" inputMode="decimal" required /></Field>
                    <Field><FieldLabel htmlFor="shipment-source">Dispatch from</FieldLabel><Input id="shipment-source" name="source_location" maxLength={120} required /></Field>
                    <Field><FieldLabel htmlFor="shipment-destination">Planned destination</FieldLabel><Input id="shipment-destination" name="destination_location" maxLength={120} required /></Field>
                    <Field><FieldLabel htmlFor="shipment-note">Shipment note (optional)</FieldLabel><Input id="shipment-note" name="note" maxLength={240} /></Field>
                  </div>
                </FieldGroup>
                <p className="text-xs text-muted-foreground">Sending from {organizationName} · account {organizationAccountNumber}</p>
                <Button type="submit" disabled={pending || batches.length === 0}>
                  {pending && <Spinner data-icon="inline-start" />}
                  Prepare shipment
                </Button>
              </form>
            ) : (
              <Alert><AlertTitle>{isOwner ? 'Create a batch first' : 'Owner access required'}</AlertTitle><AlertDescription>{isOwner ? 'A shipment must reference a real product batch.' : 'Only an organization owner can create shipment records.'}</AlertDescription></Alert>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Shipment trace</CardTitle>
          <CardDescription>Each status is backed by an immutable event containing its actor organization and timestamp.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {shipments.length ? shipments.map((shipment) => {
            const isSender = shipment.sender_organization_id === organizationId
            const actionKey = pendingAction?.startsWith(`${shipment.id}:`) ? pendingAction : undefined
            return (
              <article key={shipment.id} className="rounded-xl border p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-medium">{shipment.product_name}</h3>
                      <Badge variant="outline">{shipment.batch_code}</Badge>
                      <Badge variant={shipment.status === 'REJECTED' ? 'destructive' : 'secondary'}>{shipment.status.replaceAll('_', ' ')}</Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{formattedQuantity(shipment.quantity, shipment.unit)} · {shipment.sender_name} → {shipment.recipient_name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{shipment.source_location} → {shipment.destination_location} · {new Date(shipment.created_at).toLocaleString()}</p>
                  </div>
                  {isSender && isOwner && shipment.status === 'PREPARED' && <Button size="sm" disabled={Boolean(pendingAction)} onClick={() => transition(shipment, 'dispatch')}>{actionKey && <Spinner data-icon="inline-start" />}Dispatch</Button>}
                  {isSender && isOwner && shipment.status === 'DISPATCHED' && <Button size="sm" disabled={Boolean(pendingAction)} onClick={() => transition(shipment, 'transit')}>{actionKey && <Spinner data-icon="inline-start" />}Mark in transit</Button>}
                  {!isSender && isOwner && ['PREPARED', 'DISPATCHED', 'IN_TRANSIT'].includes(shipment.status) && (
                    <div className="flex flex-wrap gap-2">
                      {shipment.status !== 'PREPARED' && <Button size="sm" disabled={Boolean(pendingAction)} onClick={() => setReceivingShipmentId(receivingShipmentId === shipment.id ? undefined : shipment.id)}>Receive</Button>}
                      <Button size="sm" variant="outline" disabled={Boolean(pendingAction)} onClick={() => setRejectingShipmentId(rejectingShipmentId === shipment.id ? undefined : shipment.id)}>Reject</Button>
                    </div>
                  )}
                </div>

                {receivingShipmentId === shipment.id && (
                  <form className="mt-4 flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-end" onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); void transition(shipment, 'receive', { destination_location: String(form.get('destination_location') ?? '').trim() }) }}>
                    <Field className="flex-1"><FieldLabel htmlFor={`receive-location-${shipment.id}`}>Actual receiving location</FieldLabel><Input id={`receive-location-${shipment.id}`} name="destination_location" defaultValue={shipment.destination_location} maxLength={120} required /></Field>
                    <Button type="submit" disabled={Boolean(pendingAction)}>{pendingAction?.startsWith(`${shipment.id}:receive:`) && <Spinner data-icon="inline-start" />}Confirm receipt</Button>
                  </form>
                )}
                {rejectingShipmentId === shipment.id && (
                  <form className="mt-4 flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-end" onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); void transition(shipment, 'reject', { reason: String(form.get('reason') ?? '').trim() }) }}>
                    <Field className="flex-1"><FieldLabel htmlFor={`reject-reason-${shipment.id}`}>Reason for rejection</FieldLabel><Input id={`reject-reason-${shipment.id}`} name="reason" maxLength={240} required /></Field>
                    <Button type="submit" variant="destructive" disabled={Boolean(pendingAction)}>{pendingAction?.startsWith(`${shipment.id}:reject:`) && <Spinner data-icon="inline-start" />}Confirm rejection</Button>
                  </form>
                )}

                <div className="mt-4 border-t pt-4">
                  <ShipmentProgress status={shipment.status} />
                  <details className="mt-3">
                    <summary className="cursor-pointer text-sm font-medium">View {shipment.events.length} trace events</summary>
                    <ol className="mt-3 flex flex-col gap-3 border-l pl-4">
                      {shipment.events.map((event) => {
                        const record = event.blockchain_record
                        const verification = verificationResults[event.id]
                        const canAnchor = ['DISPATCHED', 'IN_TRANSIT', 'RECEIVED', 'REJECTED'].includes(event.to_status)
                          && (!record || record.status === 'submission_failed')
                        const anchorLabel = !record ? 'Not anchored' : record.status === 'simulated'
                          ? 'Simulated in development'
                          : record.status === 'confirmed' ? 'Confirmed on blockchain'
                            : record.status === 'submitted' ? 'Confirmation pending'
                              : record.status === 'submitting' ? 'Submission in progress'
                                : record.status === 'submission_failed' ? 'Submission failed'
                                  : 'Blockchain transaction failed'
                        return (
                          <li key={event.id} className="relative flex flex-col gap-1">
                            <span aria-hidden="true" className="absolute -left-[21px] top-1.5 size-2 rounded-full bg-primary" />
                            <p className="text-sm font-medium">{event.from_status ? `${event.from_status.replaceAll('_', ' ')} → ` : ''}{event.to_status.replaceAll('_', ' ')}</p>
                            {event.detail && <p className="text-sm text-muted-foreground">{event.detail}</p>}
                            <p className="text-xs text-muted-foreground">{new Date(event.created_at).toLocaleString()} · actor {event.actor_user_id.slice(0, 8)} · {event.actor_organization_id === organizationId ? organizationName : isSender ? shipment.recipient_name : shipment.sender_name}</p>
                            <div className="mt-2 flex flex-col gap-2 rounded-lg bg-muted/40 p-3">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-xs font-medium">Blockchain evidence</span>
                                <Badge variant={!record ? 'outline' : record.status === 'failed' || record.status === 'submission_failed' ? 'destructive' : 'secondary'}>{anchorLabel}</Badge>
                                {record?.provider === 'development' && <span className="text-xs text-muted-foreground">No public-chain transaction</span>}
                              </div>
                              {record && (
                                <div className="flex flex-col gap-1 text-xs text-muted-foreground">
                                  <p>Digest: <code className="break-all font-mono">{record.digest}</code> · {record.digest_version}</p>
                                  <p>Provider: {record.provider} · network: {record.network}</p>
                                  {record.transaction_hash && <p>Transaction: <code className="break-all font-mono">{record.transaction_hash}</code></p>}
                                  {record.block_number !== null && <p>Block: {record.block_number}</p>}
                                </div>
                              )}
                              <div className="flex flex-wrap gap-2">
                                {isOwner && canAnchor && blockchainStatus.enabled && (
                                  <Button size="sm" variant="outline" disabled={anchorPendingEventId === event.id} onClick={() => void anchorEvidence(shipment.id, event.id)}>
                                    {anchorPendingEventId === event.id && <Spinner data-icon="inline-start" />}
                                    {record ? 'Retry evidence submission' : 'Anchor evidence'}
                                  </Button>
                                )}
                                {record && !blockchainStatus.enabled && <span className="self-center text-xs text-muted-foreground">Blockchain anchoring is disabled.</span>}
                                <Button size="sm" variant="ghost" disabled={verificationPendingEventId === event.id} onClick={() => void verifyEvidence(shipment.id, event.id)}>
                                  {verificationPendingEventId === event.id && <Spinner data-icon="inline-start" />}
                                  Verify history &amp; evidence
                                </Button>
                              </div>
                              {verification && (
                                <p role="status" aria-live="polite" className={`text-xs ${verification.integrity_warning || !verification.history_consistent ? 'text-destructive' : 'text-muted-foreground'}`}>
                                  {verification.history_consistent ? 'Internal history is consistent.' : 'Internal history is inconsistent.'}{' '}
                                  {verification.blockchain_status === 'SIMULATED'
                                    ? 'Evidence is simulated in development only; no public-chain transaction exists.'
                                    : verification.blockchain_status === 'ANCHORED_MATCH'
                                      ? 'The digest matches independently verified blockchain evidence.'
                                      : verification.blockchain_status === 'ANCHORED_MISMATCH'
                                        ? 'Blockchain evidence mismatch. Do not rely on this anchor.'
                                        : verification.blockchain_status === 'CONFIRMATION_PENDING'
                                          ? 'Submission exists; blockchain confirmation is pending.'
                                          : verification.blockchain_status === 'VERIFICATION_UNAVAILABLE'
                                            ? 'An anchor record exists, but the current provider configuration cannot independently verify it.'
                                            : 'No blockchain anchor was found for this event.'}
                                </p>
                              )}
                            </div>
                          </li>
                        )
                      })}
                    </ol>
                  </details>
                </div>
              </article>
            )
          }) : (
            <Empty>
              <EmptyHeader><EmptyTitle>No shipments yet</EmptyTitle><EmptyDescription>Prepared dispatches and partner receipts will appear here as an auditable trace.</EmptyDescription></EmptyHeader>
            </Empty>
          )}
          {hasMoreShipments && <Button variant="outline" onClick={loadMoreShipments} disabled={loadingMore} className="self-center">{loadingMore && <Spinner data-icon="inline-start" />}{loadingMore ? 'Loading shipments…' : 'Load more shipments'}</Button>}
        </CardContent>
      </Card>
    </section>
  )
}
