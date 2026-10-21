import { BookOpenIcon, FileCheckIcon, LockIcon, RotateCcwIcon } from 'lucide-react'
import Link from 'next/link'

const assurances = [
  {
    icon: LockIcon,
    title: 'Nothing moves until you confirm',
    body: 'You review the internal LedgerChain account transfer before confirming it.',
  },
  {
    icon: FileCheckIcon,
    title: 'An internal ledger record',
    body: 'The backend returns a payment and ledger reference after the internal transfer commits.',
  },
  {
    icon: RotateCcwIcon,
    title: 'Safe to retry',
    body: 'Retrying the same request reuses its idempotency key. A lost response may still leave the outcome unknown.',
  },
]

export function PaymentAside() {
  return (
    <aside aria-labelledby="payment-aside-title" className="flex flex-col gap-5 lg:sticky lg:top-10">
      <div className="flex flex-col gap-4 rounded-xl border bg-card p-5">
        <h2 id="payment-aside-title" className="text-sm font-semibold">
          How your payment is protected
        </h2>
        <ul className="flex flex-col gap-4">
          {assurances.map((item) => {
            const Icon = item.icon
            return (
              <li key={item.title} className="flex gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                  <Icon className="size-4" aria-hidden="true" />
                </span>
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-medium">{item.title}</span>
                  <span className="text-xs leading-relaxed text-muted-foreground">{item.body}</span>
                </div>
              </li>
            )
          })}
        </ul>
      </div>
      <Link
        href="/how-it-works#payments"
        className="flex items-center gap-2 rounded-md px-1 text-sm font-medium text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
      >
        <BookOpenIcon className="size-4" aria-hidden="true" />
        See how a payment is recorded
      </Link>
    </aside>
  )
}
