import { AlertCircleIcon, BookOpenIcon, ListIcon, type LucideIcon } from 'lucide-react'
import type { Metadata } from 'next'
import Link from 'next/link'
import { FaqList } from '@/components/guide/faq-list'
import { faqs } from '@/components/guide/guide-content'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { PageHeader } from '@/components/ledger/page-header'

export const metadata: Metadata = {
  title: 'Help & support',
  description: 'Answers to common questions and the support capabilities available in LedgerChain.',
}

const shortcuts: { href: string; icon: LucideIcon; title: string; body: string }[] = [
  { href: '/how-it-works', icon: BookOpenIcon, title: 'How LedgerChain works', body: 'A plain-language guide to records and verification.' },
  { href: '/activity', icon: ListIcon, title: 'Find a record', body: 'Search your payments and updates by reference.' },
]

export default function HelpPage() {
  return (
    <div className="flex flex-col gap-8 lg:gap-10">
      <PageHeader
        title="Help & support"
        description="Find answers to common questions and check the support capabilities currently available."
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Help & support' }]}
      />

      <nav aria-label="Help shortcuts">
        <ul className="grid gap-3 sm:grid-cols-3">
          {shortcuts.map((item) => {
            const Icon = item.icon
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="flex h-full flex-col gap-3 rounded-xl border bg-card p-4 outline-none transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <Icon className="size-5 text-primary" aria-hidden="true" />
                  <span className="flex flex-col gap-1">
                    <span className="text-sm font-semibold">{item.title}</span>
                    <span className="text-sm text-pretty text-muted-foreground">{item.body}</span>
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)]">
        <section aria-labelledby="help-faq" className="flex flex-col gap-4">
          <h2 id="help-faq" className="text-base font-semibold">
            Common questions
          </h2>
          <FaqList items={faqs} />
        </section>

        <section id="contact" aria-labelledby="help-contact" className="flex scroll-mt-20 flex-col gap-4 lg:scroll-mt-8">
          <div className="flex flex-col gap-1">
            <h2 id="help-contact" className="text-base font-semibold">
              Contact support
            </h2>
          </div>
          <Alert>
            <AlertCircleIcon aria-hidden="true" />
            <AlertTitle>In-app support tickets are unavailable</AlertTitle>
            <AlertDescription>
              The backend does not currently provide a support-ticket API. Use the support channel provided by your LedgerChain administrator, and do not send passwords or session tokens.
            </AlertDescription>
          </Alert>
        </section>
      </div>
    </div>
  )
}
