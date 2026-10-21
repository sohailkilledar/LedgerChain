import { BookOpenIcon, BoxesIcon, BoxIcon, ChevronRightIcon, LandmarkIcon, SendIcon, type LucideIcon } from 'lucide-react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface Action {
  label: string
  description: string
  icon: LucideIcon
  href?: string
}

const available: (Action & { href: string })[] = [
  { label: 'Send an internal payment', description: 'Transfer to a LedgerChain account', icon: SendIcon, href: '/payments/new' },
  { label: 'Manage products', description: 'Create and review product records', icon: BoxIcon, href: '/products' },
  { label: 'Manage inventory', description: 'Record stock and trace movements', icon: BoxesIcon, href: '/inventory' },
  { label: 'Register an asset', description: 'Record ownership and history', icon: LandmarkIcon, href: '/assets' },
]

export function QuickActions() {
  return (
    <Card className="gap-0">
      <CardHeader className="pb-3">
        <CardTitle>Quick actions</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <ul className="flex flex-col gap-1">
          {available.map((action) => {
            const Icon = action.icon
            return (
              <li key={action.label}>
                <Link
                  href={action.href}
                  className="group/action -mx-2 flex items-center gap-3 rounded-lg p-2 outline-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                    <Icon className="size-4" aria-hidden="true" />
                  </span>
                  <span className="flex flex-1 flex-col">
                    <span className="text-sm font-medium">{action.label}</span>
                    <span className="text-xs text-muted-foreground">{action.description}</span>
                  </span>
                  <ChevronRightIcon
                    className="size-4 text-muted-foreground transition-transform group-hover/action:translate-x-0.5"
                    aria-hidden="true"
                  />
                </Link>
              </li>
            )
          })}
        </ul>
      </CardContent>
    </Card>
  )
}

export function GuidePromo() {
  return (
    <Link
      href="/how-it-works"
      className="group/guide flex items-start gap-3 rounded-xl border border-dashed p-4 outline-none transition-colors hover:border-primary/40 hover:bg-accent/50 focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
        <BookOpenIcon className="size-4" aria-hidden="true" />
      </span>
      <span className="flex flex-1 flex-col gap-0.5">
        <span className="text-sm font-medium">New to LedgerChain?</span>
        <span className="text-xs leading-relaxed text-muted-foreground">
          Learn how every record is created, confirmed, and verified — no technical knowledge needed.
        </span>
      </span>
      <ChevronRightIcon
        className="mt-2 size-4 shrink-0 text-muted-foreground transition-transform group-hover/guide:translate-x-0.5"
        aria-hidden="true"
      />
    </Link>
  )
}
