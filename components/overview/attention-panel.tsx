import { ChevronRightIcon, CircleCheckIcon } from 'lucide-react'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { statusIcons, statusToneClass } from '@/components/ledger/status-badge'
import { kindLabels } from '@/lib/ledger/format'
import type { ActivityRecord } from '@/lib/ledger/types'
import { cn } from '@/lib/utils'

const actionLabel: Partial<Record<ActivityRecord['status'], string>> = {
  action_required: 'Action needed',
  failed: 'Review what happened',
}

export function AttentionPanel({ records }: { records: ActivityRecord[] }) {
  return (
    <Card className="h-full gap-0">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2">
          Needs your attention
          {records.length > 0 && (
            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-[0.6875rem] font-semibold text-primary-foreground tabular-nums">
              {records.length}
            </span>
          )}
        </CardTitle>
        <CardDescription>
          {records.length === 0 ? 'Nothing to do right now.' : 'Handle these to keep things moving.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1">
        {records.length === 0 ? (
          <Empty className="h-full border py-8">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <CircleCheckIcon aria-hidden="true" />
              </EmptyMedia>
              <EmptyTitle>{"You're all caught up"}</EmptyTitle>
              <EmptyDescription>No failed or rejected records were found in the latest activity items.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <ul className="flex flex-col gap-2">
            {records.map((record) => {
              const Icon = statusIcons[record.status]
              return (
                <li key={record.id}>
                  <Link
                    href={`/activity?record=${record.id}`}
                    className="group/item flex items-start gap-3 rounded-lg border p-3 outline-none transition-colors hover:border-foreground/20 hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span
                      className={cn(
                        'flex size-8 shrink-0 items-center justify-center rounded-full',
                        statusToneClass[record.status],
                      )}
                    >
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <span className="text-sm font-medium text-pretty">{record.title}</span>
                      <span className="text-xs text-muted-foreground">
                        {kindLabels[record.kind]} · {actionLabel[record.status] ?? 'View'}
                      </span>
                    </span>
                    <ChevronRightIcon
                      className="mt-2 size-4 shrink-0 text-muted-foreground transition-transform group-hover/item:translate-x-0.5"
                      aria-hidden="true"
                    />
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
