'use client'

import { useEffect, useRef, useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { ledgerService, newIdempotencyKey } from '@/lib/ledger/service'
import type { BackendInventoryBatch, BackendInventoryMovement, BackendInventoryStock, BackendProduct, InventoryMovementRequest } from '@/lib/ledger/api-client'

const operations: { value: InventoryMovementRequest['movement_type']; label: string }[] = [
  { value: 'stock_in', label: 'Receive stock' },
  { value: 'stock_out', label: 'Dispatch stock' },
  { value: 'movement', label: 'Move between locations' },
  { value: 'adjustment', label: 'Adjust counted stock' },
]

type AdjustmentDirection = 'increase' | 'decrease'

function quantity(value: string | number | null, unit?: string | null) {
  if (value === null) return '—'
  const formatted = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 3 }).format(Number(value))
  return unit ? `${formatted} ${unit}` : formatted
}

function movementDescription(movement: BackendInventoryMovement) {
  const amount = movement.adjustment_delta ?? movement.quantity
  const value = quantity(amount, movement.unit)
  if (movement.movement_type === 'stock_in') return `${value} received at ${movement.destination_location}`
  if (movement.movement_type === 'stock_out') return `${value} dispatched from ${movement.source_location}`
  if (movement.movement_type === 'movement') return `${value} moved from ${movement.source_location} to ${movement.destination_location}`
  return `${value} adjustment at ${movement.destination_location}${movement.reason ? ` · ${movement.reason}` : ''}`
}

export function InventoryManager({
  initialStocks,
  initialMovements,
  products,
  batches,
  initialHasMoreStocks,
  initialHasMoreMovements,
}: {
  initialStocks: BackendInventoryStock[]
  initialMovements: BackendInventoryMovement[]
  products: BackendProduct[]
  batches: BackendInventoryBatch[]
  initialHasMoreStocks: boolean
  initialHasMoreMovements: boolean
}) {
  const [stocks, setStocks] = useState(initialStocks)
  const [movements, setMovements] = useState(initialMovements)
  const [hasMoreStocks, setHasMoreStocks] = useState(initialHasMoreStocks)
  const [hasMoreMovements, setHasMoreMovements] = useState(initialHasMoreMovements)
  const [operation, setOperation] = useState<InventoryMovementRequest['movement_type']>('stock_in')
  const [selectedProductId, setSelectedProductId] = useState('')
  const [adjustmentDirection, setAdjustmentDirection] = useState<AdjustmentDirection>('increase')
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [loadingStocks, setLoadingStocks] = useState(false)
  const [loadingMovements, setLoadingMovements] = useState(false)
  const [error, setError] = useState<string>()
  const [notice, setNotice] = useState<string>()
  const requestKeys = useRef(new Map<string, string>())

  useEffect(() => {
    setStocks(initialStocks)
    setMovements(initialMovements)
    setHasMoreStocks(initialHasMoreStocks)
    setHasMoreMovements(initialHasMoreMovements)
  }, [initialStocks, initialMovements, initialHasMoreStocks, initialHasMoreMovements])

  async function loadStocks() {
    setLoadingStocks(true)
    setError(undefined)
    try {
      const page = await ledgerService.listInventoryStockPage({ limit: 50, offset: stocks.length })
      setStocks((current) => [...current, ...page.items])
      setHasMoreStocks(page.has_more)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load additional inventory locations.')
    } finally {
      setLoadingStocks(false)
    }
  }

  async function loadMovements() {
    setLoadingMovements(true)
    setError(undefined)
    try {
      const page = await ledgerService.listInventoryMovementPage({ limit: 50, offset: movements.length })
      setMovements((current) => [...current, ...page.items])
      setHasMoreMovements(page.has_more)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load additional movements.')
    } finally {
      setLoadingMovements(false)
    }
  }

  async function submitMovement(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const amount = String(form.get('quantity') ?? '').trim()
    const selectedProduct = String(form.get('product_id') ?? '')
    const payload: Omit<InventoryMovementRequest, 'organization_id'> = {
      product_id: selectedProduct,
      movement_type: operation,
      quantity: amount,
    }
    const source = String(form.get('source_location') ?? '').trim()
    const destination = String(form.get('destination_location') ?? '').trim()
    const reason = String(form.get('reason') ?? '').trim()
    const threshold = String(form.get('low_stock_threshold') ?? '').trim()
    if (source) payload.source_location = source
    if (destination) payload.destination_location = destination
    const batchId = String(form.get('batch_id') ?? '')
    if (batchId) payload.batch_id = batchId
    if (reason) payload.reason = reason
    if (threshold) payload.low_stock_threshold = threshold
    if (operation === 'adjustment') {
      const absoluteAmount = Number(amount)
      payload.adjustment_delta = String(adjustmentDirection === 'increase' ? absoluteAmount : -absoluteAmount)
    }

    const requestFingerprint = JSON.stringify(payload)
    const idempotencyKey = requestKeys.current.get(requestFingerprint) ?? newIdempotencyKey()
    requestKeys.current.set(requestFingerprint, idempotencyKey)
    setPending(true)
    setError(undefined)
    setNotice(undefined)
    try {
      const created = await ledgerService.createInventoryMovement(payload, idempotencyKey)
      requestKeys.current.delete(requestFingerprint)
      setMovements((current) => [created, ...current.filter((item) => item.id !== created.id)])
      setIsFormOpen(false)
      formElement.reset()
      setOperation('stock_in')
      setAdjustmentDirection('increase')
      setSelectedProductId('')
      setNotice('Inventory movement recorded. The event is now part of your organization’s activity history.')
      try {
        const page = await ledgerService.listInventoryStockPage({ limit: 50, offset: 0 })
        setStocks(page.items)
        setHasMoreStocks(page.has_more)
      } catch {
        setNotice('Inventory movement recorded. The stock balance could not be refreshed, so reload the page to confirm the latest quantity.')
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The inventory movement was not confirmed.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-2xl text-sm text-muted-foreground">Available stock is tracked by product and location. Every change records its actor, reason, before-and-after quantity, and timestamp.</p>
        <Button onClick={() => { setIsFormOpen((open) => !open); setError(undefined); setNotice(undefined) }} disabled={products.length === 0}>
          {isFormOpen ? 'Close form' : 'Record movement'}
        </Button>
      </div>

      {error && <Alert variant="destructive"><AlertTitle>Movement not confirmed</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      {notice && <Alert><AlertTitle>Inventory updated</AlertTitle><AlertDescription>{notice}</AlertDescription></Alert>}

      {isFormOpen && (
        <Card>
          <CardHeader>
            <CardTitle>Record an inventory event</CardTitle>
            <CardDescription>Stock is updated atomically. Stock-outs and movements cannot exceed available quantity.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={submitMovement} className="flex flex-col gap-5">
              <FieldGroup>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field>
                    <FieldLabel htmlFor="inventory-operation">Operation</FieldLabel>
                    <select id="inventory-operation" value={operation} onChange={(event) => setOperation(event.target.value as InventoryMovementRequest['movement_type'])} className="h-10 rounded-lg border border-input bg-card px-3 text-sm">
                      {operations.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                    </select>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="inventory-product">Product / SKU</FieldLabel>
                    <select id="inventory-product" name="product_id" value={selectedProductId} onChange={(event) => setSelectedProductId(event.target.value)} required className="h-10 rounded-lg border border-input bg-card px-3 text-sm">
                      <option value="">Select a product</option>
                      {products.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}
                    </select>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="inventory-batch">Batch / lot (optional)</FieldLabel>
                    <select id="inventory-batch" name="batch_id" className="h-10 rounded-lg border border-input bg-card px-3 text-sm">
                      <option value="">Unbatched stock</option>
                      {batches.filter((batch) => batch.product_id === selectedProductId).map((batch) => <option key={batch.id} value={batch.id}>{batch.batch_code}</option>)}
                    </select>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="inventory-quantity">{operation === 'adjustment' ? 'Quantity change' : 'Quantity'}</FieldLabel>
                    <Input id="inventory-quantity" name="quantity" type="number" min="0.001" step="0.001" inputMode="decimal" required />
                  </Field>
                  {operation === 'adjustment' && (
                    <Field>
                      <FieldLabel htmlFor="inventory-adjustment-direction">Adjustment</FieldLabel>
                      <select id="inventory-adjustment-direction" value={adjustmentDirection} onChange={(event) => setAdjustmentDirection(event.target.value as AdjustmentDirection)} className="h-10 rounded-lg border border-input bg-card px-3 text-sm">
                        <option value="increase">Increase counted stock</option>
                        <option value="decrease">Decrease counted stock</option>
                      </select>
                    </Field>
                  )}
                  {(operation === 'stock_out' || operation === 'movement') && (
                    <Field>
                      <FieldLabel htmlFor="inventory-source">{operation === 'movement' ? 'Source location' : 'Dispatch from'}</FieldLabel>
                      <Input id="inventory-source" name="source_location" required maxLength={120} />
                    </Field>
                  )}
                  {(operation !== 'stock_out') && (
                    <Field>
                      <FieldLabel htmlFor="inventory-destination">{operation === 'movement' ? 'Destination location' : operation === 'adjustment' ? 'Location to adjust' : 'Receive at'}</FieldLabel>
                      <Input id="inventory-destination" name="destination_location" required maxLength={120} />
                    </Field>
                  )}
                  {operation !== 'movement' && (
                    <Field>
                      <FieldLabel htmlFor="inventory-threshold">Low-stock threshold (optional)</FieldLabel>
                      <Input id="inventory-threshold" name="low_stock_threshold" type="number" min="0" step="0.001" inputMode="decimal" />
                    </Field>
                  )}
                  {operation === 'adjustment' && (
                    <Field className="sm:col-span-2">
                      <FieldLabel htmlFor="inventory-reason">Adjustment reason</FieldLabel>
                      <Input id="inventory-reason" name="reason" required maxLength={240} />
                    </Field>
                  )}
                </div>
              </FieldGroup>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" onClick={() => setIsFormOpen(false)} disabled={pending}>Cancel</Button>
                <Button type="submit" disabled={pending || products.length === 0}>
                  {pending && <Spinner data-icon="inline-start" />}
                  {pending ? 'Recording…' : 'Save inventory event'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {!products.length && (
        <Alert>
          <AlertTitle>Create a product first</AlertTitle>
          <AlertDescription>Inventory quantities are attached to real product records. Add a product before receiving stock.</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(20rem,0.85fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Available stock</CardTitle>
            <CardDescription>Current quantity by organization-owned product and location.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {stocks.length ? stocks.map((stock) => (
              <div key={stock.id} className="flex flex-col gap-2 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex min-w-0 flex-col gap-1">
                  <p className="truncate font-medium">{stock.product_name}</p>
                  <p className="truncate font-mono text-xs text-muted-foreground">{stock.sku} · {stock.location}{stock.batch_code ? ` · Lot ${stock.batch_code}` : ''}</p>
                  {stock.low_stock_threshold !== null && <p className="text-xs text-muted-foreground">Low-stock threshold: {quantity(stock.low_stock_threshold, stock.unit)}</p>}
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-lg font-semibold tabular-nums">{quantity(stock.quantity, stock.unit)}</span>
                  <Badge variant={stock.is_low_stock ? 'destructive' : 'secondary'}>{stock.is_low_stock ? 'Low stock' : 'Available'}</Badge>
                </div>
              </div>
            )) : (
              <Empty className="py-10">
                <EmptyHeader>
                  <EmptyMedia variant="icon"><span className="font-mono text-sm">0</span></EmptyMedia>
                  <EmptyTitle>No stock recorded</EmptyTitle>
                  <EmptyDescription>Record a receipt to establish the first quantity for a product and location.</EmptyDescription>
                </EmptyHeader>
                {products.length > 0 && <Button variant="outline" onClick={() => setIsFormOpen(true)}>Receive stock</Button>}
              </Empty>
            )}
            {hasMoreStocks && <Button variant="outline" onClick={loadStocks} disabled={loadingStocks} className="self-center">{loadingStocks && <Spinner data-icon="inline-start" />}{loadingStocks ? 'Loading locations…' : 'Load more locations'}</Button>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Movement history</CardTitle>
            <CardDescription>Immutable record of real inventory changes.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {movements.length ? movements.map((movement) => (
              <article key={movement.id} className="border-l-2 border-border pl-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium">{movement.product_name}</p>
                  <Badge variant="outline">{movement.movement_type.replaceAll('_', ' ')}</Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{movementDescription(movement)}</p>
                {movement.source_quantity_before !== null && movement.source_quantity_after !== null && (
                  <p className="mt-1 text-xs text-muted-foreground">Source: {quantity(movement.source_quantity_before, movement.unit)} → {quantity(movement.source_quantity_after, movement.unit)}</p>
                )}
                {movement.destination_quantity_before !== null && movement.destination_quantity_after !== null && (
                  <p className="mt-1 text-xs text-muted-foreground">Destination: {quantity(movement.destination_quantity_before, movement.unit)} → {quantity(movement.destination_quantity_after, movement.unit)}</p>
                )}
                <p className="mt-1 text-xs text-muted-foreground">{new Date(movement.created_at).toLocaleString()} · {movement.sku}{movement.batch_code ? ` · Lot ${movement.batch_code}` : ''}</p>
                <p className="mt-1 break-all font-mono text-[11px] text-muted-foreground">Event {movement.id}</p>
              </article>
            )) : (
              <Empty className="py-10">
                <EmptyHeader>
                  <EmptyMedia variant="icon"><span className="font-mono text-sm">—</span></EmptyMedia>
                  <EmptyTitle>No movement history</EmptyTitle>
                  <EmptyDescription>Recorded receipts, dispatches, movements, and adjustments will appear here.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
            {hasMoreMovements && <Button variant="outline" onClick={loadMovements} disabled={loadingMovements} className="self-center">{loadingMovements && <Spinner data-icon="inline-start" />}{loadingMovements ? 'Loading events…' : 'Load more history'}</Button>}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

