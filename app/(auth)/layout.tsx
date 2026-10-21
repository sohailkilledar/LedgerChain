import { FileCheck2Icon, SearchCheckIcon, ShieldCheckIcon } from 'lucide-react'
import { Logo } from '@/components/shell/logo'

const pillars = [
  {
    icon: FileCheck2Icon,
    title: 'Record',
    body: 'Payments, shipments, and asset events are recorded in their organization-scoped histories.',
  },
  {
    icon: ShieldCheckIcon,
    title: 'Verify',
    body: 'Supported records keep append-only history; later changes add events instead of rewriting prior events.',
  },
  {
    icon: SearchCheckIcon,
    title: 'Review',
    body: 'Review application history separately from optional blockchain evidence and its honest confirmation status.',
  },
]

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)] xl:grid-cols-[minmax(0,1fr)_minmax(0,32rem)]">
      <div className="flex flex-col px-4 py-6 sm:px-8">
        <header>
          <Logo />
        </header>
        <main id="main" className="flex flex-1 items-center justify-center py-10">
          <div className="flex w-full max-w-sm animate-enter flex-col gap-6">{children}</div>
        </main>
        <footer className="text-xs text-muted-foreground">
          {'© 2026 LedgerChain · Trusted records for business'}
        </footer>
      </div>

      <aside
        aria-label="About LedgerChain"
        className="hidden flex-col justify-center gap-10 border-l bg-card px-10 py-12 lg:flex xl:px-14"
      >
        <div className="flex flex-col gap-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-primary">Why businesses use LedgerChain</p>
          <p className="text-2xl font-semibold tracking-tight text-balance">
            Records your partners can trust without taking your word for it.
          </p>
        </div>
        <ol className="flex flex-col">
          {pillars.map((pillar, index) => {
            const Icon = pillar.icon
            return (
              <li key={pillar.title} className="relative flex gap-4 pb-7 last:pb-0">
                {index < pillars.length - 1 && (
                  <span aria-hidden="true" className="absolute top-10 bottom-1 left-5 w-px bg-border" />
                )}
                <span className="flex size-10 shrink-0 items-center justify-center rounded-full border bg-background text-primary">
                  <Icon className="size-4.5" aria-hidden="true" />
                </span>
                <div className="flex flex-col gap-1 pt-1.5">
                  <h2 className="text-sm font-semibold">{pillar.title}</h2>
                  <p className="text-sm leading-relaxed text-muted-foreground">{pillar.body}</p>
                </div>
              </li>
            )
          })}
        </ol>
      </aside>
    </div>
  )
}
