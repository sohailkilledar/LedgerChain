import { EyeIcon, LayersIcon, ScrollTextIcon, ShieldCheckIcon, UsersIcon, type LucideIcon } from 'lucide-react'
import type { Metadata } from 'next'
import { PageHeader } from '@/components/ledger/page-header'
import { RecordDisclosure } from '@/components/ledger/record-disclosure'
import { FaqList } from '@/components/guide/faq-list'
import { FlowDiagram } from '@/components/guide/flow-diagram'
import {
  assetFlow,
  faqs,
  financeFlow,
  glossary,
  howFlow,
  supplyFlow,
  whyFlow,
} from '@/components/guide/guide-content'
import { GuideSection } from '@/components/guide/guide-section'
import { getServerActivity } from '@/lib/ledger/server-service'

export const metadata: Metadata = {
  title: 'How LedgerChain works',
  description: 'A plain-language guide to how LedgerChain records, verifies, and tracks payments, products, and assets.',
}

const contents = [
  { id: 'what', label: 'What is LedgerChain?' },
  { id: 'why', label: 'Why a ledger?' },
  { id: 'how', label: 'How it works' },
  { id: 'payments', label: 'Finance' },
  { id: 'supply-chain', label: 'Supply chain' },
  { id: 'assets', label: 'Assets' },
  { id: 'records', label: 'Reading a record' },
  { id: 'terms', label: 'Common terms' },
  { id: 'faq', label: 'FAQ' },
]

const pillars: { icon: LucideIcon; title: string; body: string }[] = [
  { icon: ScrollTextIcon, title: 'Record', body: 'Supported payment and asset actions are committed by the backend to PostgreSQL.' },
  { icon: ShieldCheckIcon, title: 'Verify', body: 'Check application-level history and any optional blockchain digest anchor as separate results.' },
  { icon: EyeIcon, title: 'Track', body: 'Review payments and asset provenance; product movement tracking is not currently available.' },
]

const recordLevels = [
  { level: 'Basic information', body: 'What happened, the amount, and the status. This is all most people need.' },
  { level: 'Transaction details', body: 'Who was involved, the reference, fees, and the date. Open with "Show details".' },
  { level: 'Technical information', body: 'Backend identifiers and blockchain proof appear only when the relevant API returns them.' },
]

export default async function HowItWorksPage() {
  const { records } = await getServerActivity({ limit: 100 })
  const sample = records.find((record) => record.kind === 'payment')

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="How LedgerChain works"
        description="A plain-language guide to the current backend, database, ledger, and optional blockchain integration."
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'How it works' }]}
      />

      <div className="grid items-start gap-10 xl:grid-cols-[minmax(0,1fr)_13rem]">
        <div className="flex min-w-0 flex-col gap-14">
          <GuideSection
            id="what"
            eyebrow="1 · The basics"
            title="What is LedgerChain?"
            description="LedgerChain connects an authenticated web app to a FastAPI backend and PostgreSQL. The backend records internal account transfers, product catalog entries, and individual asset provenance."
          >
            <ul className="grid gap-3 sm:grid-cols-3">
              {pillars.map((pillar) => {
                const Icon = pillar.icon
                return (
                  <li key={pillar.title} className="flex flex-col gap-3 rounded-xl border bg-card p-5">
                    <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                      <Icon className="size-5" aria-hidden="true" />
                    </span>
                    <div className="flex flex-col gap-1">
                      <span className="font-semibold">{pillar.title}</span>
                      <span className="text-sm leading-relaxed text-muted-foreground">{pillar.body}</span>
                    </div>
                  </li>
                )
              })}
            </ul>
          </GuideSection>

          <GuideSection
            id="why"
            eyebrow="2 · The reason"
            title="Why LedgerChain supports blockchain anchors"
            description="The backend database is authoritative for application records. Blockchain anchoring is a separate, optional digest/reference proof and does not establish that source information is true."
          >
            <FlowDiagram steps={whyFlow} label="From action to verifiable history" />
            <div className="flex items-start gap-3 rounded-xl border border-dashed p-4 text-sm leading-relaxed text-muted-foreground">
              <UsersIcon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <p>
                <span className="font-medium text-foreground">In short:</span> fewer disputes, easier audits, and proof
                you can share when someone asks {'"did this really happen?"'}
              </p>
            </div>
          </GuideSection>

          <GuideSection
            id="how"
            eyebrow="3 · Step by step"
            title="How LedgerChain works"
            description="Supported actions are validated by the backend and committed according to their domain rules. Optional blockchain anchoring runs separately."
          >
            <FlowDiagram steps={howFlow} label="How an action becomes a verified record" numbered />
          </GuideSection>

          <GuideSection
            id="payments"
            eyebrow="4 · Example"
            title="Finance: sending a payment"
            description="After confirmation, the backend performs an internal INR account transfer and double-entry ledger posting. It is not an external bank settlement."
          >
            <FlowDiagram steps={financeFlow} label="How a payment is recorded" />
          </GuideSection>

          <GuideSection
            id="supply-chain"
            eyebrow="5 · Example"
            title="Products and linked assets"
            description="Products are catalog records. Individual assets can be linked to a product and maintain separate ownership, custody, and provenance events; product movement events are not available."
          >
            <FlowDiagram steps={supplyFlow} label="How a product's journey is recorded" />
          </GuideSection>

          <GuideSection
            id="assets"
            eyebrow="6 · Example"
            title="Assets: proving ownership"
            description="Registered assets keep a complete ownership history, so it is always clear who owns what, and since when."
          >
            <FlowDiagram steps={assetFlow} label="How asset ownership is recorded" />
          </GuideSection>

          <GuideSection
            id="records"
            eyebrow="7 · Reading a record"
            title="Understanding a ledger record"
            description="Records are layered so you see the outcome first and only dig deeper when you need to."
          >
            <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,16rem)_minmax(0,1fr)]">
              <ol className="flex flex-col gap-3" aria-label="Levels of a record">
                {recordLevels.map((item, index) => (
                  <li key={item.level} className="flex gap-3">
                    <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold tabular-nums">
                      {index + 1}
                    </span>
                    <div className="flex flex-col gap-0.5">
                      <span className="flex items-center gap-1.5 text-sm font-semibold">
                        <LayersIcon className="size-3.5 text-muted-foreground" aria-hidden="true" />
                        {item.level}
                      </span>
                      <span className="text-xs leading-relaxed text-muted-foreground">{item.body}</span>
                    </div>
                  </li>
                ))}
              </ol>
              {sample && (
                <figure className="flex flex-col gap-2">
                  <RecordDisclosure record={sample} />
                  <figcaption className="text-xs text-muted-foreground">
                    An example record. Try opening the details and technical information.
                  </figcaption>
                </figure>
              )}
            </div>
          </GuideSection>

          <GuideSection
            id="terms"
            eyebrow="8 · Vocabulary"
            title="Common terms"
            description="You may see these words in technical details. Here is what they mean in everyday language."
          >
            <dl className="grid gap-3 sm:grid-cols-2">
              {glossary.map((entry) => (
                <div key={entry.term} className="flex flex-col gap-1 rounded-xl border bg-card p-4">
                  <dt className="text-sm font-semibold">{entry.term}</dt>
                  <dd className="text-sm leading-relaxed text-pretty text-muted-foreground">{entry.meaning}</dd>
                </div>
              ))}
            </dl>
          </GuideSection>

          <GuideSection id="faq" eyebrow="9 · Questions" title="Frequently asked questions">
            <FaqList items={faqs} />
          </GuideSection>
        </div>

        <nav aria-label="On this page" className="sticky top-8 hidden flex-col gap-3 xl:flex">
          <span className="text-xs font-semibold text-muted-foreground">On this page</span>
          <ul className="flex flex-col gap-0.5 border-l">
            {contents.map((item) => (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  className="-ml-px block border-l border-transparent py-1 pl-3 text-sm text-muted-foreground outline-none transition-colors hover:border-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </div>
  )
}
