'use client'

import { ChevronRightIcon } from 'lucide-react'
import { Fragment, useState } from 'react'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { formatDate, formatMoney, kindLabels } from '@/lib/ledger/format'
import type { ActivityRecord } from '@/lib/ledger/types'
import { CopyButton } from './copy-button'
import { KindIcon } from './kind-icon'
import { RecordDisclosure } from './record-disclosure'
import { StatusBadge } from './status-badge'

const timeFormatter = new Intl.DateTimeFormat('en-IN', {
  hour: 'numeric',
  minute: '2-digit',
  timeZone: 'Asia/Kolkata',
})

function groupByDay(records: ActivityRecord[]) {
  const groups: { label: string; records: ActivityRecord[] }[] = []
  for (const record of records) {
    const label = formatDate(record.createdAt)
    const last = groups[groups.length - 1]
    if (last?.label === label) last.records.push(record)
    else groups.push({ label, records: [record] })
  }
  return groups
}

export function ActivityList({
  records,
  groupByDate = false,
  initialSelectedId,
}: {
  records: ActivityRecord[]
  groupByDate?: boolean
  initialSelectedId?: string
}) {
  const [selected, setSelected] = useState<ActivityRecord | null>(
    () => records.find((record) => record.id === initialSelectedId) ?? null,
  )
  const groups = groupByDate ? groupByDay(records) : [{ label: '', records }]

  return (
    <>
      <div className="flex flex-col">
        {groups.map((group) => (
          <Fragment key={group.label || 'all'}>
            {group.label && (
              <h3 className="sticky top-14 z-10 border-b bg-muted/60 px-4 py-2 text-xs font-medium text-muted-foreground backdrop-blur md:px-5 lg:top-0">
                {group.label}
              </h3>
            )}
            <ul className="flex flex-col divide-y">
              {group.records.map((record) => (
                <li key={record.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(record)}
                    aria-haspopup="dialog"
                    className="group/row flex w-full items-center gap-3 px-4 py-3.5 text-left outline-none transition-colors hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset sm:gap-4 md:px-5"
                  >
                    <KindIcon kind={record.kind} />
                    <div className="flex min-w-0 flex-1 flex-col gap-1">
                      <span className="flex items-baseline justify-between gap-3">
                        <span className="truncate text-sm font-medium">{record.title}</span>
                        {record.amount && (
                          <span className="shrink-0 text-sm font-semibold tabular-nums sm:hidden">
                            {formatMoney(record.amount)}
                          </span>
                        )}
                      </span>
                      <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                        <span className="truncate">{record.counterparty}</span>
                        <span aria-hidden="true">·</span>
                        <time dateTime={record.createdAt}>
                          {groupByDate ? timeFormatter.format(new Date(record.createdAt)) : formatDate(record.createdAt)}
                        </time>
                        <StatusBadge status={record.status} className="sm:hidden" />
                      </span>
                    </div>
                    <div className="hidden shrink-0 flex-col items-end gap-1.5 sm:flex">
                      {record.amount && (
                        <span className="text-sm font-semibold tabular-nums">{formatMoney(record.amount)}</span>
                      )}
                      <StatusBadge status={record.status} />
                    </div>
                    <ChevronRightIcon
                      className="size-4 shrink-0 text-muted-foreground transition-transform group-hover/row:translate-x-0.5"
                      aria-hidden="true"
                    />
                  </button>
                </li>
              ))}
            </ul>
          </Fragment>
        ))}
      </div>

      <Sheet open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-lg">
          {selected && (
            <>
              <SheetHeader className="flex-row items-center gap-3 border-b pr-12">
                <KindIcon kind={selected.kind} />
                <div className="flex min-w-0 flex-col gap-0.5">
                  <SheetTitle>{kindLabels[selected.kind]} record</SheetTitle>
                  <SheetDescription className="flex items-center gap-1">
                    <span className="sr-only">Reference</span>
                    <span className="truncate font-mono text-xs">{selected.reference}</span>
                    <CopyButton value={selected.reference} label="reference ID" />
                  </SheetDescription>
                </div>
              </SheetHeader>
              <div className="p-4">
                <RecordDisclosure key={selected.id} record={selected} defaultLevel={2} />
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  )
}
