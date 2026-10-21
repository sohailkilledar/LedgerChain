'use client'

import { AlertCircleIcon, CheckCircle2Icon, CircleHelpIcon, RefreshCwIcon, ShieldAlertIcon, ShieldCheckIcon } from 'lucide-react'
import { useRef, useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { ledgerService, newIdempotencyKey } from '@/lib/ledger/service'
import { verificationDescription } from '@/lib/ledger/api-client'
import type { BackendAsset, BackendBlockchainRecord, BackendBlockchainStatus, BackendEvent, BackendOwnership, BackendVerification } from '@/lib/ledger/api-client'

type Action = 'transfer' | 'custody'

function verificationLabel(status: BackendVerification['blockchain_status']) {
  if (status === 'ANCHORED_MATCH') return 'Anchored · digest matches'
  if (status === 'SIMULATED') return 'Simulated / development'
  if (status === 'ANCHORED_MISMATCH') return 'Integrity mismatch'
  if (status === 'CONFIRMATION_PENDING') return 'Confirmation pending'
  return 'Not anchored'
}

export function AssetDetail({
  initialAsset,
  initialHistory,
  initialHasMoreHistory,
  initialOwnership,
  initialHasMoreOwnership,
  initialVerification,
  initialBlockchainStatus,
}: {
  initialAsset: BackendAsset
  initialHistory: BackendEvent[]
  initialHasMoreHistory: boolean
  initialOwnership: BackendOwnership[]
  initialHasMoreOwnership: boolean
  initialVerification: BackendVerification
  initialBlockchainStatus: BackendBlockchainStatus
}) {
  const [asset, setAsset] = useState(initialAsset)
  const [history, setHistory] = useState(initialHistory)
  const [hasMoreHistory, setHasMoreHistory] = useState(initialHasMoreHistory)
  const [ownership, setOwnership] = useState(initialOwnership)
  const [hasMoreOwnership, setHasMoreOwnership] = useState(initialHasMoreOwnership)
  const [verification, setVerification] = useState(initialVerification)
  const [blockchainStatus] = useState(initialBlockchainStatus)
  const [anchorRecord, setAnchorRecord] = useState<BackendBlockchainRecord>()
  const [anchorNotice, setAnchorNotice] = useState<string>()
  const [anchoringEventId, setAnchoringEventId] = useState<string>()
  const [action, setAction] = useState<Action>()
  const [accountNumber, setAccountNumber] = useState('')
  const [error, setError] = useState<string>()
  const [pending, setPending] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [loadingOwnership, setLoadingOwnership] = useState(false)
  const mutationKeys = useRef(new Map<string, string>())

  function idempotencyKey(operation: Action | 'retire', value = '') {
    const scope = `${operation}:${value}`
    const existing = mutationKeys.current.get(scope)
    if (existing) return existing
    const key = newIdempotencyKey()
    mutationKeys.current.set(scope, key)
    return key
  }

  function clearIdempotencyKey(operation: Action | 'retire', value = '') {
    mutationKeys.current.delete(`${operation}:${value}`)
  }

  async function reload() {
    const [nextAsset, nextHistory, nextOwnership, nextVerification] = await Promise.all([
      ledgerService.getAsset(asset.id),
      ledgerService.getAssetHistory(asset.id, { limit: 50, offset: 0 }),
      ledgerService.getAssetOwnership(asset.id, { limit: 50, offset: 0 }),
      ledgerService.verifyAsset(asset.id),
    ])
    setAsset(nextAsset)
    setHistory(nextHistory.items)
    setHasMoreHistory(nextHistory.has_more)
    setOwnership(nextOwnership.items)
    setHasMoreOwnership(nextOwnership.has_more)
    setVerification(nextVerification)
  }

  async function loadMoreHistory() {
    setLoadingHistory(true)
    setError(undefined)
    try {
      const page = await ledgerService.getAssetHistory(asset.id, { limit: 50, offset: history.length })
      setHistory((current) => [...current, ...page.items])
      setHasMoreHistory(page.has_more)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'More provenance history could not be loaded.')
    } finally {
      setLoadingHistory(false)
    }
  }

  async function loadMoreOwnership() {
    setLoadingOwnership(true)
    setError(undefined)
    try {
      const page = await ledgerService.getAssetOwnership(asset.id, { limit: 50, offset: ownership.length })
      setOwnership((current) => [...current, ...page.items])
      setHasMoreOwnership(page.has_more)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'More ownership history could not be loaded.')
    } finally {
      setLoadingOwnership(false)
    }
  }

  async function anchorEvent(eventId: string) {
    setAnchoringEventId(eventId)
    setError(undefined)
    setAnchorNotice(undefined)
    try {
      const record = await ledgerService.anchorAssetEvent(asset.id, eventId)
      setAnchorRecord(record)
      const label = record.status === 'simulated' ? 'SIMULATED / DEVELOPMENT' : record.status.toUpperCase().replaceAll('_', ' ')
      setAnchorNotice(`Provider ${record.provider} returned ${label} for this event.`)
      try {
        setVerification(await ledgerService.verifyAsset(asset.id))
      } catch {
        setAnchorNotice(`The anchor response was recorded as ${label}; refreshed verification is unavailable.`)
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The blockchain anchor was not confirmed.')
    } finally {
      setAnchoringEventId(undefined)
    }
  }

  async function refreshVerification() {
    setRefreshing(true)
    setError(undefined)
    try {
      setVerification(await ledgerService.verifyAsset(asset.id))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Verification could not be refreshed.')
    } finally {
      setRefreshing(false)
    }
  }

  async function submitAction(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!action) return
    setPending(true)
    setError(undefined)
    try {
      const value = accountNumber.replace(/\s/g, '')
      if (action === 'transfer') {
        await ledgerService.transferAsset(asset.id, value, idempotencyKey('transfer', value))
        await reload()
        clearIdempotencyKey('transfer', value)
      } else {
        await ledgerService.changeAssetCustody(asset.id, value, idempotencyKey('custody', value))
        await reload()
        clearIdempotencyKey('custody', value)
      }
      setAction(undefined)
      setAccountNumber('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The asset update could not be recorded.')
    } finally {
      setPending(false)
    }
  }

  async function retireAsset() {
    if (!window.confirm('Retire this asset? This change is permanent and will be added to its history.')) return
    setPending(true)
    setError(undefined)
    try {
      await ledgerService.retireAsset(asset.id, idempotencyKey('retire'))
      await reload()
      clearIdempotencyKey('retire')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The asset could not be retired.')
    } finally {
      setPending(false)
    }
  }

  const blockchainTone = verification.blockchain_status === 'ANCHORED_MATCH'
    ? 'default'
    : verification.blockchain_status === 'ANCHORED_MISMATCH'
      ? 'destructive'
      : 'secondary'

  return (
    <div className="flex flex-col gap-5">
      {error && (
        <Alert variant="destructive">
          <AlertCircleIcon aria-hidden="true" />
          <AlertTitle>Asset operation not completed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{asset.name}</CardTitle>
            <CardDescription>{asset.category} · Identifier {asset.asset_identifier}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {asset.description && <p className="text-sm text-muted-foreground">{asset.description}</p>}
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <div><dt className="text-xs text-muted-foreground">Asset ID</dt><dd className="break-all font-mono text-xs">{asset.id}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Owner organization</dt><dd className="break-all font-mono text-xs">{asset.current_owner_organization_id}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Custodian</dt><dd className="break-all font-mono text-xs">{asset.current_custodian_organization_id ?? 'Not assigned'}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Status</dt><dd className="font-medium capitalize">{asset.status}</dd></div>
            </dl>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => setAction(action === 'transfer' ? undefined : 'transfer')} disabled={asset.status !== 'active' || pending}>Transfer ownership</Button>
              <Button variant="outline" size="sm" onClick={() => setAction(action === 'custody' ? undefined : 'custody')} disabled={asset.status !== 'active' || pending}>Change custody</Button>
              <Button variant="destructive" size="sm" onClick={retireAsset} disabled={asset.status !== 'active' || pending}>Retire asset</Button>
            </div>
            {action && (
              <form onSubmit={submitAction} className="rounded-lg border bg-muted/20 p-4">
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor="destination-account-number">{action === 'transfer' ? 'Recipient account number' : 'Custodian account number'}</FieldLabel>
                    <Input
                      id="destination-account-number"
                      value={accountNumber}
                      onChange={(event) => setAccountNumber(event.target.value.replace(/\s/g, ''))}
                      inputMode="numeric"
                      maxLength={18}
                      pattern="[0-9]{9,18}"
                      required
                      autoComplete="off"
                      aria-describedby="destination-account-help"
                    />
                    <p id="destination-account-help" className="text-xs text-muted-foreground">Enter the 9–18 digit LedgerChain account number. The account must be active.</p>
                  </Field>
                </FieldGroup>
                <div className="mt-3 flex justify-end gap-2">
                  <Button type="button" variant="ghost" onClick={() => setAction(undefined)} disabled={pending}>Cancel</Button>
                  <Button type="submit" disabled={pending || !/^\d{9,18}$/.test(accountNumber.replace(/\s/g, ''))}>
                    {pending && <Spinner data-icon="inline-start" />}
                    {pending ? 'Recording…' : action === 'transfer' ? 'Record transfer' : 'Update custody'}
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div className="flex flex-col gap-1">
                <CardTitle>Verification</CardTitle>
                <CardDescription>Application history consistency and blockchain anchoring are reported separately.</CardDescription>
              </div>
              <Button variant="outline" size="icon-sm" aria-label="Refresh asset verification" onClick={refreshVerification} disabled={refreshing}>
                {refreshing ? <Spinner /> : <RefreshCwIcon aria-hidden="true" />}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-2">
              {verification.integrity_warning ? <ShieldAlertIcon className="size-4 text-destructive" aria-hidden="true" /> : verification.history_consistent ? <ShieldCheckIcon className="size-4 text-success" aria-hidden="true" /> : <CircleHelpIcon className="size-4 text-warning" aria-hidden="true" />}
              <Badge variant={blockchainTone}>{verificationLabel(verification.blockchain_status)}</Badge>
              <Badge variant="outline">{blockchainStatus.provider === 'development' || blockchainStatus.health === 'simulated' ? 'SIMULATED / DEVELOPMENT' : blockchainStatus.provider}</Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              {blockchainStatus.enabled ? `Network: ${blockchainStatus.network}` : 'Blockchain anchoring is disabled in this environment.'}
            </p>
            <p className="text-sm text-muted-foreground">{verificationDescription(verification.blockchain_status)}</p>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div><dt className="text-xs text-muted-foreground">Record exists</dt><dd className="font-medium">{verification.exists ? 'Yes' : 'No'}</dd></div>
              <div><dt className="text-xs text-muted-foreground">History consistent</dt><dd className="font-medium">{verification.history_consistent ? 'Yes' : 'No'}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Recorded events</dt><dd className="font-medium tabular-nums">{verification.event_count}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Integrity warning</dt><dd className="font-medium">{verification.integrity_warning ? 'Yes' : 'No'}</dd></div>
            </dl>
            {verification.latest_anchor_record_event_id && (
              <p className="break-all border-t pt-3 text-xs text-muted-foreground">
                Latest anchored event: <span className="font-mono text-foreground">{verification.latest_anchor_record_event_id}</span>
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Provenance history</CardTitle><CardDescription>Append-only events returned by the backend.</CardDescription></CardHeader>
          <CardContent>
            {history.length ? (
              <ol className="flex flex-col gap-4">
                {history.map((event) => (
                  <li key={event.id} className="border-l-2 border-border pl-4">
                    <p className="font-medium capitalize">{event.event_type.replaceAll('_', ' ')}</p>
                    <p className="text-xs text-muted-foreground">Event {event.sequence_number} · {new Date(event.created_at).toLocaleString()}</p>
                    <p className="mt-1 break-all font-mono text-[11px] text-muted-foreground">{event.id}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {verification.latest_anchor_record_event_id === event.id && <Badge variant={blockchainTone}>{verificationLabel(verification.blockchain_status)}</Badge>}
                      {blockchainStatus.enabled && verification.latest_anchor_record_event_id !== event.id && (
                        <Button variant="outline" size="sm" onClick={() => anchorEvent(event.id)} disabled={anchoringEventId !== undefined}>
                          {anchoringEventId === event.id && <Spinner data-icon="inline-start" />}
                          {anchoringEventId === event.id ? 'Submitting anchor…' : 'Anchor this event'}
                        </Button>
                      )}
                      {!blockchainStatus.enabled && <span className="text-xs text-muted-foreground">Anchoring disabled</span>}
                    </div>
                    {anchorRecord?.asset_event_id === event.id && (
                      <div className="mt-3 flex flex-col gap-2 rounded-md border bg-muted/20 p-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium">Anchor response</span>
                          <Badge variant={anchorRecord.status === 'failed' || anchorRecord.status === 'submission_failed' ? 'destructive' : 'secondary'}>
                            {anchorRecord.status === 'simulated' ? 'SIMULATED / DEVELOPMENT' : anchorRecord.status.replaceAll('_', ' ')}
                          </Badge>
                        </div>
                        {anchorNotice && <p className="text-xs text-muted-foreground">{anchorNotice}</p>}
                        <p className="break-all font-mono text-[11px] text-muted-foreground">Digest · {anchorRecord.digest}</p>
                        {anchorRecord.transaction_hash && <p className="break-all font-mono text-[11px] text-muted-foreground">Transaction · {anchorRecord.transaction_hash}</p>}
                        {anchorRecord.block_number !== null && <p className="text-xs text-muted-foreground">Block {anchorRecord.block_number}{anchorRecord.confirmed_at ? ` · Confirmed ${new Date(anchorRecord.confirmed_at).toLocaleString()}` : ''}</p>}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            ) : <p className="text-sm text-muted-foreground">No history events have been returned.</p>}
            {hasMoreHistory && (
              <Button variant="outline" onClick={loadMoreHistory} disabled={loadingHistory}>
                {loadingHistory && <Spinner data-icon="inline-start" />}
                {loadingHistory ? 'Loading history…' : 'Load more provenance events'}
              </Button>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Ownership history</CardTitle><CardDescription>Ownership records returned by the backend.</CardDescription></CardHeader>
          <CardContent>
            {ownership.length ? (
              <ol className="flex flex-col gap-3">
                {ownership.map((entry) => (
                  <li key={entry.id} className="border-b pb-3 last:border-0 last:pb-0">
                    <p className="break-all font-mono text-xs">{entry.organization_id}</p>
                    <p className="mt-1 text-xs text-muted-foreground">Recorded {new Date(entry.created_at).toLocaleString()}</p>
                    <p className="mt-1 break-all font-mono text-[11px] text-muted-foreground">Event {entry.event_id}</p>
                  </li>
                ))}
              </ol>
            ) : <p className="text-sm text-muted-foreground">No ownership history has been returned.</p>}
            {hasMoreOwnership && (
              <Button variant="outline" onClick={loadMoreOwnership} disabled={loadingOwnership}>
                {loadingOwnership && <Spinner data-icon="inline-start" />}
                {loadingOwnership ? 'Loading history…' : 'Load more ownership records'}
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
