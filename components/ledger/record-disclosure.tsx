'use client'

import { ChevronDownIcon, ShieldCheckIcon } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { formatDateTime, formatMoney, shortenHash } from '@/lib/ledger/format'
import type { ActivityRecord } from '@/lib/ledger/types'
import { cn } from '@/lib/utils'
import { CopyButton } from './copy-button'
import { StatusBadge, statusIcons, statusToneClass } from './status-badge'
import { TermHint } from './term-hint'

type Level = 1 | 2 | 3

/**
 * Three-level progressive disclosure for any ledger-backed record.
 * Level 1: human-readable outcome. Level 2: useful details. Level 3: technical record.
 */
export function RecordDisclosure({
  record,
  defaultLevel = 1,
  className,
}: {
  record: ActivityRecord
  defaultLevel?: Level
  className?: string
}) {
  const [showDetails, setShowDetails] = useState(defaultLevel >= 2)
  const [showTechnical, setShowTechnical] = useState(defaultLevel >= 3)
  const Icon = statusIcons[record.status]
  const verified = record.status === 'completed' && record.technical

  return (
    <section
      aria-labelledby={`${record.id}-title`}
      className={cn('flex flex-col overflow-hidden rounded-xl border bg-card text-card-foreground', className)}
    >
      {/* Level 1 — outcome */}
      <div className="flex flex-col gap-4 p-5">
        <div className="flex items-start gap-4">
          <span
            className={cn(
              'flex size-10 shrink-0 items-center justify-center rounded-full',
              statusToneClass[record.status],
            )}
          >
            <Icon className="size-5" aria-hidden="true" />
          </span>
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <h3 id={`${record.id}-title`} className="text-base font-semibold text-balance">
                {record.title}
              </h3>
              <StatusBadge status={record.status} />
            </div>
            <p className="text-sm leading-relaxed text-muted-foreground text-pretty">{record.summary}</p>
          </div>
        </div>
        {(record.amount || verified) && (
          <div className="flex flex-wrap items-end justify-between gap-3 rounded-lg bg-muted/50 px-4 py-3">
            {record.amount && (
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">Amount</span>
                <span className="text-xl font-semibold tracking-tight tabular-nums">{formatMoney(record.amount)}</span>
              </div>
            )}
            {verified && (
              <span className="flex items-center gap-1.5 text-xs font-medium text-success">
                <ShieldCheckIcon className="size-3.5" aria-hidden="true" />
                Verified on the ledger
              </span>
            )}
          </div>
        )}
      </div>

      {/* Level 2 — details */}
      <Collapsible open={showDetails} onOpenChange={setShowDetails} className="border-t">
        <CollapsibleTrigger
          render={
            <Button variant="ghost" className="h-11 w-full justify-between rounded-none px-5 font-medium" />
          }
        >
          {showDetails ? 'Hide details' : 'Show details'}
          <ChevronDownIcon
            data-icon="inline-end"
            aria-hidden="true"
            className={cn('transition-transform duration-200', showDetails && 'rotate-180')}
          />
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="flex flex-col gap-5 px-5 pt-1 pb-5">
            <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
              {record.details.map((field) => (
                <div key={field.label} className="flex min-w-0 flex-col gap-1">
                  <dt className="text-xs font-medium text-muted-foreground">{field.label}</dt>
                  <dd className="flex items-center gap-1 text-sm font-medium">
                    <span className={cn('min-w-0 break-words', field.copyable && 'font-mono text-[0.8125rem]')}>
                      {field.value}
                    </span>
                    {field.copyable && <CopyButton value={field.value} label={field.label} />}
                  </dd>
                </div>
              ))}
              <div className="flex flex-col gap-1">
                <dt className="text-xs font-medium text-muted-foreground">Date</dt>
                <dd className="text-sm font-medium">{formatDateTime(record.createdAt)}</dd>
              </div>
            </dl>

            {/* Level 3 — technical record */}
            {record.technical ? (
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
                    <span className="flex items-center gap-2">
                      {showTechnical ? 'Hide technical details' : 'View technical details'}
                      <span className="rounded-sm bg-card px-1.5 py-px text-[0.6875rem] font-normal text-muted-foreground ring-1 ring-border">
                        For auditors
                      </span>
                    </span>
                    <ChevronDownIcon
                      data-icon="inline-end"
                      aria-hidden="true"
                      className={cn('transition-transform duration-200', showTechnical && 'rotate-180')}
                    />
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <TechnicalList technical={record.technical} />
                  </CollapsibleContent>
                </div>
              </Collapsible>
            ) : (
              <p className="rounded-lg border border-dashed px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">
                No ledger record was created for this action, so there are no technical details to show.
              </p>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </section>
  )
}

function TechnicalList({ technical }: { technical: NonNullable<ActivityRecord['technical']> }) {
  const rows: { term: string; explanation: string; value: string; copy?: string }[] = [
    {
term: 'EVM transaction hash',
    explanation: 'An identifier for a real EVM transaction. Simulated development anchors do not have one.',
      value: shortenHash(technical.transactionHash, 8),
      copy: technical.transactionHash,
    },
    {
      term: 'Block number',
      explanation: 'The position on the ledger where this record was permanently added.',
      value: `#${technical.blockNumber.toLocaleString('en-IN')}`,
    },
    {
      term: 'Confirmations',
      explanation: 'How many later records have been added since. More confirmations mean the record is more settled.',
      value: technical.confirmations.toLocaleString('en-IN'),
    },
    {
      term: 'Contract',
      explanation: 'The program on the ledger that applied the rules for this action.',
      value: shortenHash(technical.contractAddress, 6),
      copy: technical.contractAddress,
    },
    {
      term: 'Network',
      explanation: 'Which LedgerChain ledger this record lives on.',
      value: technical.network,
    },
    {
      term: 'Gas used',
      explanation: 'The amount of processing work needed to record this action.',
      value: technical.gasUsed.toLocaleString('en-IN'),
    },
    {
      term: 'Ledger timestamp (UTC)',
      explanation: 'The exact time the ledger accepted this record, in Coordinated Universal Time.',
      value: technical.timestamp.replace('T', ' ').replace(/\.\d+Z$|Z$/, ''),
    },
  ]

  return (
    <div className="flex flex-col gap-4 border-t px-3 py-4">
      <p className="rounded-md bg-warning-soft px-2.5 py-1.5 text-xs text-warning">
        Prototype data — these technical values are simulated and do not exist on a live ledger.
      </p>
      <p className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground">
        <ShieldCheckIcon className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
        These details describe the permanent ledger record. They can be shared with an auditor or
        support team to independently verify this action.
      </p>
      <dl className="flex flex-col divide-y">
        {rows.map((row) => (
          <div
            key={row.term}
            className="flex flex-col gap-1 py-2 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
          >
            <dt className="text-xs text-muted-foreground">
              <TermHint term={row.term} explanation={row.explanation} />
            </dt>
            <dd className="flex items-center gap-1 font-mono text-xs break-all">
              {row.value}
              {row.copy && <CopyButton value={row.copy} label={row.term} />}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
