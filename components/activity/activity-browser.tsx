'use client'

import { AlertCircleIcon, InboxIcon } from 'lucide-react'
import { useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { ActivityList } from '@/components/ledger/activity-list'
import { ledgerService } from '@/lib/ledger/service'
import { Spinner } from '@/components/ui/spinner'
import type { ActivityKind, ActivityRecord } from '@/lib/ledger/types'

type KindFilter = 'all' | ActivityKind
const kindFilters: { value: KindFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'payment', label: 'Payments' },
  { value: 'finance', label: 'Finance' },
  { value: 'inventory', label: 'Inventory' },
  { value: 'shipment', label: 'Shipments' },
  { value: 'asset', label: 'Assets' },
  { value: 'blockchain', label: 'Evidence' },
]

export function ActivityBrowser({
  records: initialRecords,
  hasMore: initialHasMore,
  initialSelectedId,
}: {
  records: ActivityRecord[]
  hasMore: boolean
  initialSelectedId?: string
}) {
  const [records, setRecords] = useState(initialRecords)
  const [hasMore, setHasMore] = useState(initialHasMore)
  const [loadingMore, setLoadingMore] = useState(false)
  const [loadError, setLoadError] = useState<string>()
  const [kind, setKind] = useState<KindFilter>('all')

  async function loadMore() {
    setLoadingMore(true)
    setLoadError(undefined)
    try {
      const page = await ledgerService.listActivityPage({ limit: 50, offset: records.length })
      setRecords((current) => [...current, ...page.records])
      setHasMore(page.hasMore)
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Could not load additional records.')
    } finally {
      setLoadingMore(false)
    }
  }

  const visible = kind === 'all' ? records : records.filter((record) => record.kind === kind)
  const countFor = (value: KindFilter) =>
    value === 'all' ? records.length : records.filter((record) => record.kind === value).length
  const filtered = kind !== 'all'

  function reset() {
    setKind('all')
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="-mx-4 overflow-x-auto px-4 md:mx-0 md:px-0">
          <ToggleGroup
            aria-label="Filter activity by type"
            variant="outline"
            value={[kind]}
            onValueChange={(value) => value[0] && setKind(value[0] as KindFilter)}
          >
            {kindFilters.map((f) => (
              <ToggleGroupItem key={f.value} value={f.value} className="h-9 gap-1.5 px-3">
                {f.label}
                <span className="text-xs font-normal text-muted-foreground tabular-nums">{countFor(f.value)}</span>
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
      </div>

      <p className="sr-only" role="status" aria-live="polite">
        {`Showing ${visible.length} ${visible.length === 1 ? 'item' : 'items'}`}
      </p>

      <Card className="gap-0 py-0">
        {visible.length > 0 ? (
          <ActivityList records={visible} groupByDate initialSelectedId={initialSelectedId} />
        ) : (
          <Empty className="py-16">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <InboxIcon aria-hidden="true" />
              </EmptyMedia>
              <EmptyTitle>Nothing matches these filters</EmptyTitle>
              <EmptyDescription>
                Try a different type or status. New activity appears here with its full record as soon as it happens.
              </EmptyDescription>
            </EmptyHeader>
            {filtered && (
              <EmptyContent>
                <Button variant="outline" onClick={reset}>
                  Clear filters
                </Button>
              </EmptyContent>
            )}
          </Empty>
        )}
      </Card>
      {loadError && (
        <Alert variant="destructive">
          <AlertCircleIcon aria-hidden="true" />
          <AlertDescription>{loadError}</AlertDescription>
        </Alert>
      )}
      {hasMore && (
        <Button variant="outline" onClick={loadMore} disabled={loadingMore} className="self-center">
          {loadingMore && <Spinner data-icon="inline-start" />}
          {loadingMore ? 'Loading records…' : 'Load more activity'}
        </Button>
      )}
    </div>
  )
}
