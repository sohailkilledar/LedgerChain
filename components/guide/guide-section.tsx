import type { ReactNode } from 'react'

export function GuideSection({
  id,
  eyebrow,
  title,
  description,
  children,
}: {
  id: string
  eyebrow: string
  title: string
  description?: ReactNode
  children: ReactNode
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="flex scroll-mt-20 flex-col gap-5 lg:scroll-mt-8">
      <div className="flex max-w-2xl flex-col gap-2">
        <span className="text-xs font-semibold tracking-wide text-primary uppercase">{eyebrow}</span>
        <h2 id={`${id}-title`} className="text-xl font-semibold tracking-tight text-balance">
          {title}
        </h2>
        {description && <p className="text-sm leading-relaxed text-pretty text-muted-foreground">{description}</p>}
      </div>
      {children}
    </section>
  )
}
