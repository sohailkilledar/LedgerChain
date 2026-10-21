import { ArrowRightIcon, SendIcon, ShieldCheckIcon } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { CopyButton } from '@/components/ledger/copy-button'
import { AddFundsDialog } from '@/components/overview/add-funds-dialog'
import { exactMoney } from '@/lib/ledger/api-client'
import type { BackendOrganization } from '@/lib/ledger/api-client'

export function BalanceSummary({ account }: { account: BackendOrganization }) {
  return (
    <section aria-labelledby="balance-title">
      <Card className="h-full gap-0 py-0">
        <div className="flex flex-col gap-6 p-5 sm:p-6">
          <div className="flex flex-col gap-2">
            <h2 id="balance-title" className="text-sm font-medium text-muted-foreground">
              Demo account balance
            </h2>
            <p className="text-4xl font-semibold tracking-tight tabular-nums sm:text-[2.75rem] sm:leading-none">
              {exactMoney(String(account.balance))}
            </p>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ShieldCheckIcon className="size-3.5 text-success" aria-hidden="true" />
              Account status: {account.status}
            </p>
            <p className="text-xs text-muted-foreground">Internal LedgerChain bookkeeping only. Demo funds are not bank funds and no real money moves.</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button size="lg" render={<Link href="/payments/new" />} nativeButton={false}>
              <SendIcon data-icon="inline-start" aria-hidden="true" />
              Send payment
            </Button>
            <AddFundsDialog />
            <Button size="lg" variant="outline" render={<Link href="/activity" />} nativeButton={false}>
              View activity
              <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
            </Button>
          </div>
        </div>
        <dl className="mt-auto grid grid-cols-1 divide-y border-t bg-muted/30 sm:grid-cols-2 sm:divide-x sm:divide-y-0">
          <div className="flex items-baseline justify-between gap-2 px-5 py-3.5 sm:px-6 sm:py-4">
            <dt className="text-xs font-medium text-muted-foreground">Account number</dt>
            <dd className="flex items-center gap-1 font-mono text-xs">
              {account.account_number}
              <CopyButton value={account.account_number} label="Copy account number" />
            </dd>
          </div>
          <div className="flex items-baseline justify-between gap-2 px-5 py-3.5 sm:px-6 sm:py-4">
            <dt className="text-xs font-medium text-muted-foreground">Account type</dt>
            <dd className="text-xs font-medium capitalize">{account.account_type.replaceAll('_', ' ')}</dd>
          </div>
        </dl>
      </Card>
    </section>
  )
}
